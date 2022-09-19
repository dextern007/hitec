from odoo import api, fields, models, exceptions, _
from odoo.addons import decimal_precision as dp
from lxml import etree
from odoo.exceptions import ValidationError
import json
from dateutil.relativedelta import relativedelta


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    request_id = fields.Many2one('purchase.request', string='Purchase Request')


class PurchaseRequestStage(models.Model):
    _name = "purchase.request.stage"
    _description = "Purchase Requisition Stage"
    _order = "sequence"

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(default=1)
    create_po = fields.Boolean(string='Create PO', default=False)
    final_stage = fields.Boolean(string='Final Stage', default=False)
    parent_id = fields.Many2one('purchase.request.stage', string='Next Stage', help='Will Move to Selected Stage')
    group_ids = fields.Many2many('res.groups', string='Approval Groups', help='Approval From Selected Group')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot set recursion stage.'))

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Purchase Request"
    _order = 'date_order desc, id desc'

    def _get_stage_id(self):
        return self.env['purchase.request.stage'].search([], limit=1)

    @api.onchange('stage_id')
    def _btn_approve_compute(self):
        stage = self.stage_id
        groups = stage.group_ids
        flag = True

        if len(self.env['purchase.request.stage'].search([])) >= 1:
            flag = False
      
        if not flag and stage.final_stage:
            flag = True

        if not flag:
            ir_model_data_obj = self.env['ir.model.data']
            group_name = ir_model_data_obj.search([('model', '=', 'res.groups'), ('res_id', 'in', groups.ids)])
            for grp in group_name.mapped('complete_name'):
                if not self.env.user.has_group(grp):
                    flag = True
                    break
                else:
                    flag = False

        self.approve_btn_visible = flag

    @api.onchange('stage_id')
    def _btn_create_po_compute(self):
        if len(self.purchase_ids) >= 1 :
            create_po = True
        else:
            create_po = self.stage_id.create_po
            if create_po:
                create_po = False
            else:
                create_po = True
        self.create_po_btn_visible = create_po

    name = fields.Char('Request Reference', required=True, index=True, copy=False, default='New')
    request_by = fields.Selection([('user', 'User'),('employee', 'Employee') ],default='user')
    date_order = fields.Datetime('Request Date', index=True, copy=False, default=fields.Datetime.now)
    date_approve = fields.Date('Approval Date', index=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    line_ids = fields.One2many('purchase.request.line', 'request_id', string='Request Lines')
    stage_id = fields.Many2one('purchase.request.stage', copy=False, string="State", default=_get_stage_id, track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env['hr.employee'].search([('user_id','=',self._uid)],limit=1, order='id desc'))
    user_id = fields.Many2one('res.users', string='User', index=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', 'Company', index=True,  default=lambda self: self.env.user.company_id.id)
    description = fields.Text('Description')
    purchase_ids = fields.One2many('purchase.order','request_id', string='Purchase Orders')
    approve_btn_visible = fields.Boolean(string="Approve Button Visible", compute='_btn_approve_compute')
    create_po_btn_visible = fields.Boolean(string="Approve Button Visible", compute='_btn_create_po_compute')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('purchase.request') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or _('New')

        return super(PurchaseRequest, self).create(vals)

    
    def copy(self, default=None):
        new_pr = super(PurchaseRequest, self).copy(default=default)
        for line in new_pr.line_ids:
            seller = line.product_id._select_seller(
                partner_id=line.partner_id, quantity=line.product_qty,
                date=line.request_id.date_order and line.request_id.date_order.date(), uom_id=line.product_uom)
            line.date_planned = line._get_date_planned(seller)
        return new_pr

    
    def button_approve(self):
        if not self.stage_id.final_stage :
            self.stage_id =  self.stage_id.parent_id 
        self.fields_view_get()

    
    def action_view_purchase_order(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        if len(self.purchase_ids) > 1:
            action['domain'] = [('id','in',self.purchase_ids.ids)]
            action['views'] = [(self.env.ref('purchase.purchase_order_tree').id, 'tree')]
        else:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.purchase_ids and self.purchase_ids[0].id 

        return action

    
    def create_po_btn(self):
        if not self.partner_id:
            raise ValidationError(_('Please Set Vendor in Request.'))

        if not self.line_ids:
            raise ValidationError(_('Please Create Request Line.'))

        if any (not line.product_id for line in self.line_ids):
            raise ValidationError('Please Set Product in %s'%','.join(self.line_ids.filtered(lambda r: not r.product_id).mapped('name')))

        po_obj = self.env['purchase.order']
        action = self.env.ref('purchase.purchase_form_action')
        result = action.read()[0]
        res = self.env.ref('purchase.purchase_order_form', False)
        result['views'] = [(res and res.id or False, 'form')]

        
        fiscal_position_id = self.env['account.fiscal.position'].sudo().with_context(company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
        purchase_order = po_obj.create( {
            'partner_id': self.partner_id.id,
            'currency_id': self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
            'payment_term_id': self.partner_id.property_supplier_payment_term_id.id,
            'fiscal_position_id': fiscal_position_id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'date_order': self.date_order,
            'request_id': self.id,
            
        })
        for line in self.line_ids:
            
            purchase_qty_uom = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_po_id)

            supplierinfo = line.product_id._select_seller(
                partner_id=purchase_order.partner_id,
                quantity=purchase_qty_uom,
                date=purchase_order.date_order and purchase_order.date_order.date(), 
                uom_id=line.product_id.uom_po_id
            )
            fpos = purchase_order.fiscal_position_id
            taxes = fpos.map_tax(line.product_id.supplier_taxes_id) if fpos else line.product_id.supplier_taxes_id
            if taxes:
                taxes = taxes.filtered(lambda t: t.company_id.id == self.company_id.id)

            # compute unit price
            price_unit = 0.0
            if supplierinfo:
                price_unit = self.env['account.tax'].sudo()._fix_tax_included_price_company(supplierinfo.price, line.product_id.supplier_taxes_id, taxes, self.company_id)
                if purchase_order.currency_id and supplierinfo.currency_id != purchase_order.currency_id:
                    price_unit = supplierinfo.currency_id.compute(price_unit, purchase_order.currency_id)

            # purchase line description in supplier lang
            product_in_supplier_lang = line.product_id.with_context({
                'lang': supplierinfo.name.lang,
                'partner_id': supplierinfo.name.id,
            })
            name = '[%s] %s' % (line.product_id.default_code, product_in_supplier_lang.display_name)
            if product_in_supplier_lang.description_purchase:
                name += '\n' + product_in_supplier_lang.description_purchase

            po_order_line = self.env['purchase.order.line'].create( {
                'name': line.name,
                'product_qty': purchase_qty_uom,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_po_id.id,
                'price_unit': price_unit,
                'order_id' : purchase_order.id,
                'date_planned': fields.Date.from_string(purchase_order.date_order) + relativedelta(days=int(supplierinfo.delay)),
                'taxes_id': [(6, 0, taxes.ids)],
            })
        result['res_id'] = purchase_order.id or False
        return result

class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'

    name = fields.Text(string='Description')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True)
    
    product_type = fields.Selection(related='product_id.type')
    request_id = fields.Many2one('purchase.request', string='Request Reference', index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='request_id.company_id', string='Company', store=True)
    stage_id = fields.Many2one(related='request_id.stage_id', store=True)
    partner_id = fields.Many2one('res.partner', related='request_id.partner_id', string='Partner', store=True)
    date_order = fields.Datetime(related='request_id.date_order', string='Request Date', readonly=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase


        return result
