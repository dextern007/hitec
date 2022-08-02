# -*- coding: utf-8 -*-
#################################################################################
# Author      : Niova Group ApS (<https://niova.dk/>)
# Copyright(c): 2018-Present Niova Group ApS
# License URL : https://invoice-scan.com/license/
# All Rights Reserved.
#################################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_alias_contact(self):
        invoicescan_alias = self.env.ref('niova_invoice_scan.mail_alias_invoice_scan')
        return invoicescan_alias._fields['alias_contact'].selection
    
    module_niova_invoice_scan = fields.Boolean(string='Allow the invoice to be synchronize by invoice scan')
    invscan_client_secret = fields.Char("Activation Key")
    invscan_active = fields.Boolean("Invoice Scan Activated", readonly=True, default=False)
    invscan_mail_prefix = fields.Char(string='Default Alias Name for Invoice Scan')
    invscan_mail_contact = fields.Selection(selection=_get_alias_contact, string='Alias Contact Security', help="Policy to post a message on the document using the mailgateway.")
    invscan_currency = fields.Many2one('res.currency',
                                        config_parameter="invoice_scan_currency",
                                        string='Default Currency',
                                        help="Set this default currency to use a default global currency. This will also convert the $ symbol to the selected currency to avoid using US dollar if the dollar symbol is used in the invoice.")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        invoice_scan_currency = get_param('invoice_scan_currency', default=False)
        if invoice_scan_currency:
            invoice_scan_currency = int(invoice_scan_currency)
        res.update(
            invscan_client_secret = get_param('invoice_scan_client_secret', default=False),
            invscan_active = get_param('invoice_scan_active', default=False),
            invscan_currency = invoice_scan_currency,
            invscan_mail_prefix = self.env.ref('niova_invoice_scan.mail_alias_invoice_scan').alias_name,
            invscan_mail_contact = self.env.ref('niova_invoice_scan.mail_alias_invoice_scan').alias_contact,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('invoice_scan_currency', self.invscan_currency.id)
        self.env.ref('niova_invoice_scan.mail_alias_invoice_scan').write({'alias_name': self.invscan_mail_prefix, 'alias_contact': self.invscan_mail_contact})