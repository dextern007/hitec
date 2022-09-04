import json
from urllib import response

from odoo import _, api, fields, models


class OnesteinAPIConfig(models.Model):
    _inherit = 'onestein.api.config'

    def ocr_invoice(self, document):
        res = self._request("POST", "/invoice-ocr/", data=json.dumps({
            "document": document,
            "lang": "chi_sim",
        }), headers={
            "Content-Type": "application/json"
        })
        print(res)
        return res
