# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sc360_default_approver_id = fields.Many2one(
        'res.users', 'Aprobador por defecto',
        config_parameter='sc360.default_approver_id',
    )
