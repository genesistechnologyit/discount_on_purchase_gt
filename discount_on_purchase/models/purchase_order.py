from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')],string='Discount Type',default='percent')
    discount_rate = fields.Float('Discount')
    discount_amount = fields.Monetary(string='Discount Amount', readonly=True, compute='_amount_all',track_visibility='always', store=True)
    enable_discount = fields.Boolean(compute='check_discount_enable')

    @api.depends('company_id.enable_discount')
    def check_discount_enable(self):
        for rec in self:
            rec.enable_discount = rec.company_id.enable_discount

    def compute_discount(self):
        for rec in self:
            if rec.discount_type == "amount":
                rec.discount_amount = rec.discount_rate if rec.amount_untaxed > 0 else 0
            elif rec.discount_type == "percent":
                if rec.discount_rate != 0.0:
                    rec.discount_amount = (rec.amount_untaxed + rec.amount_tax) * rec.discount_rate / 100
                else:
                    rec.discount_amount = 0
            elif not rec.discount_type:
                rec.discount_amount = 0
                rec.discount_rate = 0
            rec.amount_total = rec.amount_untaxed + rec.amount_tax - rec.discount_amount

    @api.constrains('discount_rate')
    def check_discount_amount(self):
        if self.discount_type == "percent":
            if self.discount_rate > 100:
                raise ValidationError('Please enter percentage value less than 100 %.')

            if self.discount_rate < 0:
                raise ValidationError('Please enter positive percentage value')
        else:
            if self.discount_rate < 0 :
                raise ValidationError('Please enter positive discount amount')

            if self.discount_rate > self.amount_untaxed:
                raise ValidationError('Please enter discount amount less than actual amount')


    @api.depends('order_line.price_total', 'discount_type', 'discount_rate')
    def _amount_all(self):
        res = super(PurchaseOrder, self)._amount_all()
        for rec in self:
            rec.compute_discount()
        return res

    def action_view_invoice(self):
        res = super(PurchaseOrder, self).action_view_invoice()
        for rec in self:
            res['context']['default_discount_rate'] = rec.discount_rate
            res['context']['default_discount_type'] = rec.discount_type
        return res
