from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    discount_type = fields.Selection([('percent', 'Percentage'),('amount', 'Amount')],string='Discount Type',default='percent')
    discount_rate = fields.Float('Discount')
    discount_amount = fields.Monetary(string='Discount Amount',readonly=True,compute='_compute_amount',store=True, track_visibility='always')
    enable_discount = fields.Boolean(compute='check_discount_enable')
    purchase_discount_account_id = fields.Integer(compute='check_discount_enable')

    @api.depends('company_id.enable_discount')
    def check_discount_enable(self):
        for rec in self:
            rec.enable_discount = rec.company_id.enable_discount
            rec.purchase_discount_account_id = rec.company_id.purchase_discount_account.id

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
                rec.discount_rate = 0
                rec.discount_amount = 0
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.discount_amount
            rec.update_discount()

    @api.constrains('discount_rate')
    def check_discount_amount(self):
        if self.discount_type == "percent":
            if self.discount_rate > 100:
                raise ValidationError('Please enter percentage value less than 100 %.')

            if self.discount_rate < 0:
                raise ValidationError('Please enter positive percentage value')
        else:
            if self.discount_rate < 0:
                raise ValidationError('Please enter positive discount amount')

            if self.discount_rate > self.amount_untaxed:
                raise ValidationError('Please enter discount amount less than actual amount')

    @api.depends('line_ids.debit','line_ids.credit','line_ids.currency_id','line_ids.amount_currency','line_ids.amount_residual',
                 'line_ids.amount_residual_currency','line_ids.payment_id.state','discount_type','discount_rate')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for rec in self:
            rec.compute_discount()
            sign = rec.type in ['in_refund', 'out_refund'] and -1 or 1
            rec.amount_total_company_signed = rec.amount_total * sign
            rec.amount_total_signed = rec.amount_total * sign


    def update_discount(self):
        for rec in self:
            currency_id = rec.currency_id
            company_currency = rec.company_id.currency_id

            already_exists = self.line_ids.filtered(lambda line: line.name and line.name.find('Discount') == 0)
            payable_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'payable')
            other_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type != 'payable')
            if already_exists:
                amount = rec.discount_amount
                amount_company = amount
                if currency_id != company_currency:
                    amount_company = currency_id.with_context(date=rec.date).compute(amount_company, company_currency)

                if rec.purchase_discount_account_id and (rec.type == "in_invoice" or rec.type == "in_refund") and amount > 0:
                    if rec.type == "in_invoice":
                        if amount_company == amount:
                            already_exists.update({
                                'debit': amount < 0.0 and -amount or 0.0,
                                'credit': amount > 0.0 and amount or 0.0,
                            })
                        else:
                            already_exists.update({
                                'debit': amount_company < 0.0 and -amount_company or 0.0,
                                'credit': amount_company > 0.0 and amount_company or 0.0,
                                'currency_id': currency_id.id,
                                'amount_currency': -amount
                            })

                    else:
                        if amount_company == amount:
                            already_exists.update({
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                            })
                        else:
                            already_exists.update({
                                'debit': amount_company > 0.0 and amount_company or 0.0,
                                'credit': amount_company < 0.0 and -amount_company or 0.0,
                                'currency_id': currency_id.id,
                                'amount_currency': amount
                            })

                total_balance = sum(other_lines.mapped('balance'))
                total_amount_currency = sum(other_lines.mapped('amount_currency'))
                payable_lines.update({
                    'amount_currency': -total_amount_currency,
                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                    'credit': total_balance > 0.0 and total_balance or 0.0,
                })
            if not already_exists and rec.discount_rate > 0:
                in_draft_mode = self != self._origin
                if not in_draft_mode and rec.type == 'in_invoice':
                    rec._recompute_discount_lines()
                print()

    @api.onchange('discount_rate', 'discount_type', 'line_ids')
    def _recompute_discount_lines(self):

        for rec in self:
            currency_id = rec.currency_id
            company_currency = rec.company_id.currency_id
            type_list = ['in_invoice', 'in_refund']

            if rec.discount_rate > 0 and rec.type in type_list:
                if rec.is_invoice(include_receipts=True):
                    in_draft_mode = self != self._origin
                    name = "Discount "
                    if rec.discount_type == "amount":
                        value = "of amount #" + str(self.discount_rate)
                    elif rec.discount_type == "percent":
                        value = " @" + str(self.discount_rate) + "%"
                    else:
                        value = ''
                    name = name + value
                    payable_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'payable')
                    already_exists = self.line_ids.filtered(lambda line: line.name and line.name.find('Discount') == 0)

                    amount = self.discount_amount
                    amount_company = amount
                    if currency_id != company_currency:
                        amount_company = currency_id.with_context(date=rec.date).compute(amount_company,company_currency)

                    if already_exists:
                        if self.purchase_discount_account_id and (self.type == "in_invoice" or self.type == "in_refund"):
                            if self.type == "in_invoice":
                                if amount_company == amount:
                                    already_exists.update({
                                        'name': name,
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                else:
                                    already_exists.update({
                                        'name': name,
                                        'debit': amount_company < 0.0 and -amount_company or 0.0,
                                        'credit': amount_company > 0.0 and amount_company or 0.0,
                                        'amount_currency': -amount,
                                        'currency_id': currency_id.id
                                    })
                            else:
                                if amount_company == amount:
                                    already_exists.update({
                                        'name': name,
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    already_exists.update({
                                        'name': name,
                                        'debit': amount_company > 0.0 and amount_company or 0.0,
                                        'credit': amount_company < 0.0 and -amount_company or 0.0,
                                        'amount_currency': amount,
                                        'currency_id': currency_id.id
                                    })
                    else:
                        new_tax_line = self.env['account.move.line']
                        create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create

                        if self.purchase_discount_account_id and (self.type == "in_invoice" or self.type == "in_refund"):
                            amount = self.discount_amount
                            move_line = {
                                'move_name': self.name,
                                'name': name,
                                'price_unit': self.discount_amount,
                                'quantity': 1,
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                                'account_id': self.purchase_discount_account_id,
                                'move_id': self.id,
                                'date': self.date,
                                'exclude_from_invoice_tab': True,
                                'partner_id': payable_lines.partner_id.id,
                                'company_id': payable_lines.company_id.id,
                                'company_currency_id': payable_lines.company_currency_id.id,
                            }

                            if self.type == "in_invoice":
                                if amount_company == amount:
                                    move_line.update({
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                else:
                                    move_line.update({
                                        'debit': amount_company < 0.0 and -amount_company or 0.0,
                                        'credit': amount_company > 0.0 and amount_company or 0.0,
                                        'amount_currency': -amount,
                                        'currency_id': currency_id.id
                                    })
                            else:
                                if amount_company == amount:
                                    move_line.update({
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    move_line.update({
                                        'debit': amount_company > 0.0 and amount_company or 0.0,
                                        'credit': amount_company < 0.0 and -amount_company or 0.0,
                                        'amount_currency': amount,
                                        'currency_id': currency_id.id
                                    })
                            self.line_ids += create_method(move_line)
                            duplicate_id = self.invoice_line_ids.filtered(lambda line: line.name and line.name.find('Discount') == 0)
                            self.invoice_line_ids = self.invoice_line_ids - duplicate_id

                    if in_draft_mode:

                        payable_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type ==  'payable')
                        other_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type != 'payable')
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        payable_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })
                    else:
                        payable_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'payable')
                        other_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type != 'payable')
                        already_exists = self.line_ids.filtered(lambda line: line.name and line.name.find('Discount') == 0)
                        total_balance = sum(other_lines.mapped('balance')) + amount
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        move_line1 = {
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                        }
                        move_line2 = {
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        }
                        self.line_ids = [(1, already_exists.id, move_line1), (1, payable_lines.id, move_line2)]
                        print()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        res = super(AccountMove, self)._prepare_refund(invoice, date_invoice=None, date=None, description=None,journal_id=None)
        res['discount_rate'] = self.discount_rate
        res['discount_type'] = self.discount_type
        return res

