# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    # --- Datos generales ---
    is_construction = fields.Boolean('Proyecto de Construccion', default=False)
    client_id = fields.Many2one('res.partner', 'Cliente', tracking=True)
    supervisor_id = fields.Many2one('res.users', 'Supervisor', tracking=True)
    architect_id = fields.Many2one('res.users', 'Arquitecto', tracking=True)
    project_type = fields.Selection([
        ('admin', 'Administracion'),
        ('construction', 'Construccion'),
        ('remodel', 'Remodelacion'),
    ], string='Tipo de proyecto', default='admin', tracking=True)
    surface_area = fields.Float('Superficie M2')
    address = fields.Char('Domicilio')
    warehouse_id = fields.Many2one('stock.warehouse', 'Almacen', readonly=True)

    # --- Partidas del proyecto ---
    partition_ids = fields.One2many(
        'sc360.project.partition', 'project_id', string='Partidas',
    )

    # --- Conteos ---
    requisition_count = fields.Integer(compute='_compute_counts')
    contract_count = fields.Integer(compute='_compute_counts')
    estimation_count = fields.Integer(compute='_compute_counts')
    logbook_count = fields.Integer(compute='_compute_counts')
    purchase_count = fields.Integer(compute='_compute_counts')

    # --- KPIs ---
    total_budget = fields.Float(
        'Total presupuesto', compute='_compute_budget_kpis', store=True,
    )
    total_purchased = fields.Float(
        'Total comprado', compute='_compute_budget_kpis', store=True,
    )
    total_estimated = fields.Float(
        'Total estimado', compute='_compute_budget_kpis', store=True,
    )
    budget_variance = fields.Float(
        'Variacion', compute='_compute_budget_kpis', store=True,
    )
    overall_progress = fields.Float(
        '% Avance global', compute='_compute_budget_kpis', store=True,
        digits=(5, 2),
    )

    # ------------------------------------------------------------------
    # Create: auto-create warehouse when is_construction
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project in projects:
            if project.is_construction:
                project._create_project_warehouse()
        return projects

    def _create_project_warehouse(self):
        self.ensure_one()
        if self.warehouse_id:
            return
        code = (self.name or 'OBR')[:5].upper().replace(' ', '')
        # Ensure unique code
        existing = self.env['stock.warehouse'].search([('code', '=', code)], limit=1)
        if existing:
            code = code[:3] + str(self.id or 0)
        warehouse = self.env['stock.warehouse'].create({
            'name': self.name,
            'code': code,
            'company_id': self.company_id.id,
        })
        self.warehouse_id = warehouse.id

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def _compute_counts(self):
        for project in self:
            project.requisition_count = self.env['sc360.requisition'].search_count([
                ('project_id', '=', project.id),
            ])
            project.contract_count = self.env['sc360.contract'].search_count([
                ('project_id', '=', project.id),
            ])
            project.estimation_count = self.env['sc360.estimate'].search_count([
                ('project_id', '=', project.id),
            ])
            project.logbook_count = self.env['sc360.logbook'].search_count([
                ('project_id', '=', project.id),
            ])
            project.purchase_count = self.env['purchase.order'].search_count([
                ('sc360_project_id', '=', project.id),
            ])

    # ------------------------------------------------------------------
    # Budget KPIs
    # ------------------------------------------------------------------

    @api.depends(
        'partition_ids.budget_line_ids.amount_budget',
        'partition_ids.budget_line_ids.amount_purchased',
        'partition_ids.budget_line_ids.amount_estimated',
    )
    def _compute_budget_kpis(self):
        for project in self:
            lines = project.partition_ids.mapped('budget_line_ids')
            project.total_budget = sum(lines.mapped('amount_budget'))
            project.total_purchased = sum(lines.mapped('amount_purchased'))
            project.total_estimated = sum(lines.mapped('amount_estimated'))
            project.budget_variance = project.total_budget - (
                project.total_purchased + project.total_estimated
            )
            if project.total_budget:
                project.overall_progress = (
                    (project.total_purchased + project.total_estimated)
                    / project.total_budget * 100
                )
            else:
                project.overall_progress = 0.0

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requisiciones'),
            'res_model': 'sc360.requisition',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contratos'),
            'res_model': 'sc360.contract',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_estimations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estimaciones'),
            'res_model': 'sc360.estimate',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
        }

    def action_view_logbooks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bitacora'),
            'res_model': 'sc360.logbook',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_purchases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordenes de compra'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('sc360_project_id', '=', self.id)],
            'context': {'default_sc360_project_id': self.id},
        }
