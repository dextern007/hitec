# -*- coding: utf-8 -*-
#################################################################################
# Author      : Niova Group ApS (<https://niova.dk/>)
# Copyright(c): 2018-Present Niova Group ApS
# License URL : https://invoice-scan.com/license/
# All Rights Reserved.
#################################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountInvoiceChangeCompany(models.TransientModel):
    _name = 'account.invoice.change.company'
    _description = 'Account Invoice Change Company'
    
    new_company_id = fields.Many2one('res.company', string='New Company', required=True)
    
    def _change_company(self, invoice, new_company):
        invoice = invoice.sudo()
        if invoice.state != 'draft' or new_company == invoice.company_id:
            return False
        
        # Change company
        invoice = invoice.with_company(new_company.id).with_context(company_id=new_company.id, default_move_type=invoice.move_type)
        invoice.journal_id = invoice._get_default_journal().id
        invoice.company_id = new_company
        context = {
            'journal_id': invoice.journal_id.id, 
            'move_type': 'in_invoice',
            'default_move_type': 'in_invoice',
            'partner_id': invoice.partner_id.id,
            'company_id': invoice.company_id.id}
        invoice = invoice.with_context(context)
        if invoice.partner_id:
            invoice._onchange_partner_id()
        
        # Clear lines, because it is not doable else
        invoice.action_clear_invoice_lines()
        invoice._auto_attach_invoice_lines()
        return True

    def action_change_company(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        
        for invoice in self.env['account.move'].browse(active_ids):
            status = self._change_company(invoice, self.new_company_id)
            if status:
                invoice._cr.commit()
                if len(active_ids) == 1:
                    # Return to list view, because we cannot look at an invoice in a different company
                    # when we stays in the old company
                    action = self.env.ref('account.action_move_in_invoice_type').read()[0]
                    return action
            elif len(active_ids) == 1:
                raise UserError(_("Not able to change company in state different from draft or has the same company."))
            else:
                invoice._cr.rollback()
        return {'type': 'ir.actions.act_window_close'}
    