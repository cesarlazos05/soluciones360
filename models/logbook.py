# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models


class Logbook(models.Model):
    """Bitacora semanal de obra."""
    _name = 'sc360.logbook'
    _description = 'Bitacora de obra'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        'Nombre', compute='_compute_name', store=True,
    )
    project_id = fields.Many2one(
        'project.project', 'Proyecto', required=True, tracking=True, index=True,
        domain=[('is_construction', '=', True)],
    )
    date = fields.Date('Fecha', required=True, default=fields.Date.today)
    period_start = fields.Date(
        'Inicio de semana', compute='_compute_period', store=True,
    )
    period_end = fields.Date(
        'Fin de semana', compute='_compute_period', store=True,
    )
    author_id = fields.Many2one(
        'res.users', 'Autor', default=lambda self: self.env.user,
    )

    summary = fields.Html('Resumen de Actividades por Partida')
    progress_notes = fields.Html('Porcentaje de Avance')
    observations = fields.Html('Observaciones')
    next_week_pending = fields.Html('Pendientes Siguiente Semana')

    photo_ids = fields.Many2many(
        'ir.attachment',
        'sc360_logbook_photo_rel', 'logbook_id', 'attachment_id',
        string='Evidencias Fotograficas',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('project_id', 'date')
    def _compute_name(self):
        for rec in self:
            project_name = rec.project_id.name or ''
            date_str = rec.date.isoformat() if rec.date else ''
            rec.name = f"BIT/{project_name}/{date_str}"

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if rec.date:
                # Monday = weekday 0
                monday = rec.date - timedelta(days=rec.date.weekday())
                sunday = monday + timedelta(days=6)
                rec.period_start = monday
                rec.period_end = sunday
            else:
                rec.period_start = False
                rec.period_end = False
