from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class Company(models.Model):
    _inherit = "res.company"

    enable_discount = fields.Boolean(string="Enable Discount Po")
    purchase_discount_account = fields.Many2one('account.account', string="Purchase Discount Account")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_discount = fields.Boolean(string="Activate Discount on Purchase", related='company_id.enable_discount', readonly=False)
    purchase_discount_account = fields.Many2one('account.account', string="Purchase Discount Account", related='company_id.purchase_discount_account', readonly=False)
