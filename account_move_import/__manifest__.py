# Copyright (c) 2016-2018 Daniel Campos <danielcampos@avanzosc.es> - Avanzosc S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Move Import",
    "version": "11.0.1.0.0",
    "license": "AGPL-3",
    "author": "AvanzOSC",
    'summary': '''Account Move Import''',
    "website": "http://www.avanzosc.es",
    "depends": [
        "account",
    ],
    "data": [
        "views/account_move_import_view.xml",
        "views/account_move_view.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    'auto_install': False,
}
