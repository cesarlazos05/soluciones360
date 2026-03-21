# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SC360EstimatePeriod(models.Model):
    """Período de Estimación (Semanal/Quincenal/Mensual)"""
    _name = 'sc360.estimate.period'
    _description = 'Período de Estimación'
    _order = 'date_start desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        'Nombre',
        required=True,
        help="Ej: Semana 12, Quincena 6, Marzo 2026"
    )
    
    code = fields.Char(
        'Código',
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('sc360.estimate.period') or 'Nuevo'
    )
    
    date_start = fields.Date(
        'Fecha inicio',
        required=True
    )
    
    date_end = fields.Date(
        'Fecha fin',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('open', 'Abierto'),
        ('closed', 'Cerrado'),
    ], default='open', string='Estado', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        string='Compañía'
    )
    
    # Relaciones
    estimate_ids = fields.One2many(
        'sc360.estimate',
        'period_id',
        string='Estimaciones'
    )
    estimate_count = fields.Integer(
        compute='_compute_estimate_count',
        string='Número de estimaciones'
    )
    
    # Totales calculados
    amount_total = fields.Monetary(
        'Total estimado',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    amount_approved = fields.Monetary(
        'Total aprobado',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True
    )
    
    _sql_constraints = [
        ('date_check', 'CHECK(date_end >= date_start)', 
         'La fecha fin debe ser mayor o igual a la fecha inicio.'),
        ('code_uniq', 'UNIQUE(code)', 
         'El código del período debe ser único.'),
    ]

    @api.depends('estimate_ids')
    def _compute_estimate_count(self):
        for period in self:
            period.estimate_count = len(period.estimate_ids)

    @api.depends('estimate_ids.amount_total', 'estimate_ids.amount_approved', 'estimate_ids.state')
    def _compute_totals(self):
        for period in self:
            estimates = period.estimate_ids.filtered(lambda e: e.state in ['approved', 'paid'])
            period.amount_total = sum(period.estimate_ids.mapped('amount_total'))
            period.amount_approved = sum(estimates.mapped('amount_approved'))

    def action_open(self):
        """Abre el período para estimaciones."""
        self.write({'state': 'open'})
        return True

    def action_close(self):
        """Cierra el período."""
        self.write({'state': 'closed'})
        return True

    def action_draft(self):
        """Reabre el período."""
        self.write({'state': 'draft'})
        return True