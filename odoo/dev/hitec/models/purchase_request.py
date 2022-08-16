# Copyright 2019 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    # _name    = "hitec.purchase_request"

    partner_id = fields.Many2one(
        string = "Vendor",
        comodel_name="res.partner",
        help="Select a Vendor",
    )
    test = fields.Integer('Color Index')
   
    