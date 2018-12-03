# Copyright (c) 2020 Daniel Campos <danielcampos@avanzosc.es> - Avanzosc S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, exceptions, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    unbalance = fields.Boolean(string='Not balanced')

    @api.multi
    def assert_balanced(self):
        if self.unbalance:
            return True
        return super(AccountMove, self).assert_balanced()
