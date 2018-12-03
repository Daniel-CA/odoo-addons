.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================================
Account Move Import from CSV file
=================================

Wizard to import account move lines from a CSV file.

* The file must have at least 4 columns with, "account_move", "move_date", "account" and "name" Head Keys.
* There are two more columns with 'debit' and 'credit' head keys to add amount.
* You can also add a column with key "partner_id" or "partner_ref" or "partner_name" to add a partner link, if you add one of them you also need to add a column with key "partner_type" defining if it is "customer" or "supplier".
* If the "date_maturity" column is added date_maturity is updated in lines.
* There are two more columns with 'currency' and 'amount_currency'.
* If analytic_account key is added with analytic account name or code, it will be also linked too.
* CSV text codification must be 'utf-8'

Credits
=======

Contributors
------------
* Daniel Campos <danielcampos@avanzosc.es>
* Ana Juaristi <ajuaristio@gmail.com>
