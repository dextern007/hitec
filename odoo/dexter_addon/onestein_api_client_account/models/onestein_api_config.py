import json
from urllib import response

from odoo import _, api, fields, models


class OnesteinAPIConfig(models.Model):
    _inherit = 'onestein.api.config'

    def ocr_invoice(self, source_email, document):
        # You get the email from self or document parameter.
        # Place that email in got_email

        got_email = source_email
        if got_email == False:
            partner_config = None

        else:
            partner_id = self.env['res.partner'].search([('email', '=', got_email)], limit=1)

            # Once you get the partner by this you can get your parameter.

            partner_config = partner_id.partner_config
        res = self._request("POST", "/invoice-ocr/", data=json.dumps({
            "document": document,
            "lang": "eng",
            "config": partner_config,
        }), headers={
            "Content-Type": "application/json"
        })
        print(res)
        return res
