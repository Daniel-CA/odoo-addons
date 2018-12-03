# Copyright (c) 2018 Daniel Campos <danielcampos@avanzosc.es> - Avanzosc S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, exceptions, _
import base64
import csv
# from io import StringIO, BytesIO
# import codecs
# from docutils.nodes import row
import datetime as dt


class AccountMoveImport(models.Model):
    _name = 'account.move.import'
    _description = 'Account move import'

    def _default_journal(self):
        company_obj = self.env['res.company']
        journal_obj = self.env['account.journal']
        journal_type = self.env.context.get('journal_type', False)
        company_id = company_obj._company_default_get(
            'account.bank.statement').id
        if journal_type:
            journals = journal_obj.search([('type', '=', journal_type),
                                           ('company_id', '=', company_id)])
            if journals:
                return journals[0]
        return self.env['account.journal']

    name = fields.Char('Import')
    data = fields.Binary('File', required=True)
    filename = fields.Char('Filename')
    date = fields.Date(required=True, default=fields.Date.context_today)
    delimiter = fields.Char('Delimiter', default=',',
                            help='Default delimiter is ","')
    move_line_import_ids = fields.One2many(
        comodel_name="account.move.line.import",
        inverse_name='move_import_id', string='Move Lines to import')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True,
        default= lambda self: self.env.user.company_id.id)
    journal_id = fields.Many2one(
        'account.journal', string='Journal', default=_default_journal)
    load_by_block = fields.Boolean(string='Block loading')
    block_number = fields.Integer(string="Line number")
    

    def clean_import_moves(self):
        for move_line in self.move_line_import_ids:
            move_line.unlink()
        return True

    def action_import_moves(self):
        """Load Account moves data from the CSV file."""
        import_line_obj = self.env['account.move.line.import']
        # Decode the file data
        file_input = base64.b64decode(self.data).decode("utf-8").splitlines()
        reader_info = {}
        delimiter = self.delimiter and str(self.delimiter) or ','
        try:
            reader = csv.reader(file_input, delimiter=delimiter,
                                lineterminator='\r\n')
        except Exception:
            raise exceptions.Warning(_("Not a valid file!"))
        n = 0
        for row in reader:
            reader_info[n] = row
            n += 1
        keys = reader_info and [x.lower() for x in reader_info[0]] or False
        # check if keys exist
        test_keys = ['account', 'move_name', 'move_date']
        # dime = [t_key in keys for t_key in test_keys]
        if not isinstance(keys, list) or False in [t_key in keys for t_key in
                                                   test_keys]:
            raise exceptions.Warning(
                _("Not 'account', 'move_name' or 'mode_date' keys found"))
        del reader_info[0]
        values = {}
        #  account_move.narration = u"No errors found"
        final_error_msg = u"Error Log:"
        partner_search = 'partner_name' in keys and 'name' or \
            'partner_ref' in keys and 'ref' or 'partner_id' in keys and 'id' \
            or False
        for i in range(1, len(reader_info)+1):
            line = i + 1
            error_message = False
            field = reader_info[i]
            values = dict(zip(keys, field))
            account_data = {}
#             partner_id = account_id = False
            #  account_data = self._check_error_data(values)
            if 'error' in account_data:
                error_message = u"{}. {} {}".format(
                    line, _(u'Line Error:'), account_data['error'])
#             else:
#                 account_id = account_data['account_id']
#                 if 'partner_id' in account_data:
#                     partner_id = account_data['partner_id']
            if error_message:
                final_error_msg = u"{} \n {}".format(
                    final_error_msg, error_message)
                continue
            debit_tmp = values.get('debit', 0.0)
            if isinstance(debit_tmp, str):
                if debit_tmp.strip():
                    debit = float(debit_tmp.replace(',', '.'))
                else:
                    debit = 0.0
            else:
                debit = debit_tmp
            credit_tmp = values.get('credit', 0.0)
            if isinstance(credit_tmp, str):
                if credit_tmp.strip():
                    credit = float(credit_tmp.replace(',', '.'))
                else:
                    credit = 0.0
            else:
                credit = credit_tmp
            amount_currency_tmp = values.get('amount_currency', False)
            if amount_currency_tmp:
                if isinstance(amount_currency_tmp, str):
                    if amount_currency_tmp.strip():
                        amount_currency = float(
                            amount_currency_tmp.replace(',', '.'))
                    else:
                        amount_currency = 0.0
            else:
                amount_currency = amount_currency_tmp
            line_data = {
                'move_import_id': self.id,
                'move_name': values.get('move_name'),
                'move_type': values.get('move_type'),
                'description': values.get('description'),
                'account': values.get('account', False),
                'move_date': values.get('move_date', False),
                'debit': debit,
                'credit': credit,
                'journal_entry': values.get('journal', False),
                'partner': values.get('partner_name', False) or
                values.get('partner_ref', False) or
                values.get('partner_id', False),
                'partner_search': partner_search,
                'currency': values.get('currency', False),
                'amount_currency': amount_currency,
                'analytic_account': values.get('analytic_account', False),
                'account_replace': values.get('replace', False),
                'maturity_date': values.get('date_maturity', False),
                }
            try:
                print (u'{}'.format(line))
                import_line_obj.create(line_data)
            except Exception:
                raise exceptions.Warning(u"Line Error:{} \n {}".format(
                    line))
        # account_move.narration = (final_error_msg == u"Error Log:" and
        #                          u'No errors found' or final_error_msg)

    def _check_balance(self, move_name):
        debit = sum(self.move_line_import_ids.filtered(
            lambda x: x.move_name == move_name).mapped('debit'))
        credit = sum(self.move_line_import_ids.filtered(
            lambda x: x.move_name == move_name).mapped('credit'))
        if round(debit, 2) == round(credit, 2):
            return {move_name: 0}
        return {move_name: abs(debit - credit)}

    def _check_date(self, date):
        res = False
        if date:
            try:
                dt.datetime.strptime(date, '%Y-%m-%d')
                return True
            except ValueError:
                return res
        return res

    def _get_data_from_partner(self, partner_data, search_by):
        """ Returns account id from a given partner info
        @param partner_data: Partner to search
        @param search_by: Key to search partner
        @param partner_type: Define if it is customer or supplier
        @return: partner account id or error message
        """
        partner_obj = self.env['res.partner']
        return_data = {'exist': False}
        operator = search_by == 'partner_id' and '=' or 'ilike'
        partner = partner_obj.search([(search_by, operator, partner_data),
                                      ('is_company', '=', True)])[:1]
        if partner:
            return_data = {
                'exist': True,
                'partner_id': partner.id,
                'account_receivable_id': partner.
                property_account_receivable_id.id,
                'account_payable_id': partner.property_account_payable_id.id,
                'customer': partner.customer, 'supplier': partner.supplier,
                'reference': partner.ref
                }
        return return_data

    def action_validate_moves(self, values):
        account_obj = self.env['account.account']
        account_move_balance = log_info = {}
        for import_line in self.move_line_import_ids.filtered(
                lambda x: x.state not in ('pass', 'done')):
            log_info = {}
            log_info['date'] = self._check_date(import_line.move_date)
            if import_line.move_name not in account_move_balance:
                account_move_balance.update(
                    self._check_balance(import_line.move_name))
            log_info['balance'] = account_move_balance[import_line.move_name]
            move_types = ('other', 'liquidity', 'receivable',
                          'receivable_refund', 'payable', 'payable_refund')
            if import_line.move_type and import_line.move_type \
                    not in move_types:
                log_info['move_type'] = False
            if import_line.account:
                account = account_obj.search(
                    [('code', '=', import_line.account),
                     ('company_id', '=', self.env.user.company_id.id)])
                if not account:
                    log_info['account'] = False
            partner_data = {}
            if import_line.partner:
                partner_data = self._get_data_from_partner(
                    import_line.partner, import_line.partner_search)
                log_info['partner'] = partner_data['exist']
            if import_line.account_replace:
                if not partner_data or not log_info['partner']:
                    log_info['replace'] = False
            if import_line.currency:
                log_info['currency'] = import_line._check_currency(
                    import_line.currency, import_line.amount_currency)
            if import_line.debit < 0 or import_line.credit < 0:
                log_info['debit/credit'] = _("Wrong amount in account")
            if import_line.maturity_date:
                log_info['date_maturity'] = self._check_date(
                    import_line.maturity_date)
            if import_line.analytic_account:
                analytic_obj = self.env['account.analytic.account']
                analytic_acc = analytic_obj.search(
                    ['|', ('name', '=', import_line.analytic_account),
                     ('code', '=', import_line.analytic_account),
                     ('company_id', '=', self.env.user.company_id.id)])
                if not analytic_acc:
                    log_info['analytic_acc'] = False
            result = import_line._update_log(log_info)
            if not result:
                import_line.state = 'error'
            else:
                import_line.state = 'pass'
        return True

    def action_process_moves(self, values):
        account_lst = set(self.mapped('move_line_import_ids.move_name'))
        for account_name in account_lst:
            account_moves = set(self.move_line_import_ids.filtered(
                lambda x: x.state == 'pass' and x.move_name == account_name))
#             if self.load_by_block:
#                 account_moves = account_moves[:self.block_number]
#             remove_moves = set(self.move_line_import_ids.filtered(
#                 lambda x: x.move_name == account_name and x.state == 'error'))
#             moves = list(account_moves - remove_moves)
            self.create_account_move(account_moves, account_name)

    def create_account_move(self, account_moves, account_name):
        account_obj = self.env['account.account']
        acc_move_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        import_line_obj = self.env['account.move.line.import']
        def_journal = journal_obj.search([('type', '=', 'bank')], limit=1)
        acc_move = acc_move_obj.search(
                [('name', '=', account_name),
                 ('company_id', '=', self.env.user.company_id.id)
                 ])
        if not acc_move:
            acc_move = acc_move_obj.create({
                'name': account_name,
                'date': self.date,
                'journal_id': self.journal_id.id or def_journal.id,
                'company_id': self.env.user.company_id.id,
                'unbalance': self.load_by_block,
                #'move_type': import_line.move_type or 'other',
                })
        all_lines = []
        for import_line in account_moves:
            line_data = []
#             for import_line in self.move_line_import_ids.filtered(
#                     lambda x: x.state == 'pass' and
#                     x.move_name == account_move):
            account = partner_id = False

            partner_data = {}
            if import_line.partner:
                partner_data = self._get_data_from_partner(
                    import_line.partner, import_line.partner_search)
                partner_id = partner_data['partner_id']
            if import_line.account:
                account = account_obj.search(
                    [('code', '=', import_line.account),
                     ('company_id', '=', self.env.user.company_id.id)])
                account_id = account.id
#                 if import_line.account_replace and partner_data:
#                     partner_id = partner_data['partner_id']
#                     if partner_data['customer']:
#                         code = ref.lstrip('0')
#                         account = account_obj.filter(
#                             lambda x: x.code[-len(code):] == code and
#                             x.internal_type == 'receivable'
#                             )
#                         account_id = account and account.id or False
#                     if partner_data['supplier']:
#                         code = ref.lstrip('0')
#                         account = account_obj.filter(
#                             lambda x: x.code[-len(code):] == code and
#                             x.internal_type == 'payable'
#                             )
#                         account_id = account and account.id or False
            analytic_acc = False
            if import_line.analytic_account:
                analytic_obj = self.env['account.analytic.account']
                analytic_acc = analytic_obj.search(
                    ['|', ('name', '=', import_line.analytic_account),
                     ('code', '=', import_line.analytic_account),
                     ('company_id', '=', self.env.user.company_id.id)])
            line_data = {
                'account_id': account_id,
                'name': import_line.description,
                'partner_id': partner_id,
                'debit': import_line.debit,
                'credit': import_line.credit,
                'journal_id': acc_move.journal_id.id,
                'analytic_account_id': analytic_acc and analytic_acc.id or
                '',
                'date_maturity': import_line.maturity_date or
                import_line.move_date,
                }
            if import_line.currency:
                line_data.update(
                    import_line_obj._check_currency(
                        import_line.currency, import_line.amount_currency))
            import_line.state = 'done'
            all_lines.append((0, 0, line_data))
        try:
            acc_move.line_ids = all_lines
        except Exception as error:
            raise exceptions.Warning(u"Line Error:{} \n".format(
                str(error)))


class AccountMoveLineImport(models.Model):
    _name = 'account.move.line.import'
    _description = 'Import account move line'

    move_import_id = fields.Many2one(comodel_name='account.move.import',
                                     string='Move Import')
    journal_entry = fields.Char(string='Journal Entry')
    move_name = fields.Char(string='Account Move')
    move_type = fields.Char(string='Move Type')
    account = fields.Char(string='Account')
    partner = fields.Char(string='Partner')
    partner_search = fields.Selection([
        ('name', 'Name'),
        ('ref', 'Reference'),
        ('id', 'Partner Id')],
        string='Partner Search',
    )
    description = fields.Char(string="Label")
    move_date = fields.Char(string='Move Date')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    maturity_date = fields.Char(string='Date Maturity')
    currency = fields.Char(string='Currency')
    account_replace = fields.Boolean(
        string='Account Replace', help="Replace the base account with your"
        "own")
    amount_currency = fields.Float(string='Amount Currency')
    analytic_account = fields.Char(string='Analytic Account')
    log_info = fields.Text(string='Log Info')
    state = fields.Selection([
        ('2validate', 'To validate'),
        ('pass', 'Validated'),
        ('error', 'Error'),
        ('done', 'Processed')],
        string='Import state', default='2validate'
    )
    move_line_id = fields.Many2one(
        'account.move.line', string='Move line')

    def _check_currency(self, currency, amount):
        currency_obj = self.env['res.currency']
        res = {'currency_id': False}
        currency_id = currency_obj.search([('name', 'ilike', currency)])[:1]
        if currency_id and amount:
            res['currency_id'] = currency_id
            try:
                res['amount_currency'] = float(amount)
            except ValueError:
                res['amount_currency'] = False
        return res

    def show_move_import_log(self):
        form_view = self.env.ref(
            'account_move_import.view_move_import_line_log_form')
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.line.import',
            'views': [(form_view.id, 'form')],
            'view_id': form_view.id,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'flags': {'initial_mode': 'view'},
            'context': self.env.context,
            }

    def _update_log(self, log_info):
        log_message = ''
        log_result = True
        if 'date' in log_info:
            log_result = log_info['date']
            if not log_result:
                log_message = '{}\n'.format(
                    _('Date: Incorrect data format: YYYY-MM-DD'))
        if 'move_type' in log_info:
            log_result = log_info['move_type'] and log_result
            log_message = '{}{}\n'.format(log_message,
                                          _('Error, unknown move type'))
        if 'account' in log_info:
            log_result = log_info['account'] and log_result
            if not log_result:
                log_message = '{}{}\n'.format(log_message,
                                              _('Error, account not found'))
        if 'balance' in log_info:
            log_result = log_info['balance'] == 0 and log_result
#             if not log_result:
#                 log_message = '{}Unbalanced: {}\n'.format(log_message,
#                                                           log_info['balance'])
        if 'partner' in log_info:
            if not log_info['partner']:
                log_result = False
                log_message = '{}Partner: {}\n'.format(
                    log_message, _('Error, partner not found'))
            if 'account' in log_info and not log_info['account']:
                log_result = log_info['partner'] and log_result
        if 'debit/credit' in log_info:
            log_result = False
            log_message = '{}Debit/credit: {}\n'.format(
                log_message, _('Wrong amount in account'))
        if 'currency' in log_info:
            if not log_info['currency']['currency_id']:
                log_result = False
                log_message = '{}Currency: {}\n'.format(
                    log_message, _('Currency not found'))
            if not log_info['currency']['amount_currency']:
                log_result = False
                log_message = '{}Currency Amount: {}\n'.format(
                    log_message, _('Incorrect amount currency format'))
        if 'analytic_acc' in log_info:
            log_result = log_info['analytic_acc'] and log_result
            log_message = '{}Analytic Account: {}\n'.format(
                log_message, _('Error, Analytic account not found'))
        if 'replace' in log_info:
            log_result = False
            log_message = '{}Account replace: {}\n'.format(
                log_message, _('Parner needed to do account replace'))
        if 'date_maturity' in log_info:
            log_result = log_info['date_maturity'] and log_result
            if not log_result:
                log_message = '{}: {}\n'.format(
                    log_message, _('date_maturity: Incorrect data format'))
        self.log_info = log_message
        return log_result
