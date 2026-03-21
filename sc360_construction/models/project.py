# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    # === DATOS GENERALES DEL PROYECTO DE CONSTRUCCIÓN ===
    is_construction = fields.Boolean(
        "Proyecto de construcción",
        default=False,
        help="Marcar si es un proyecto gestionado por SC360"
    )

    # Cliente y stakeholders
    client_id = fields.Many2one(
        'res.partner',
        "Cliente",
        domain=[('is_company', '=', True)],
        tracking=True
    )
    supervisor_id = fields.Many2one(
        'res.users',
        "Supervisor de obra",
        tracking=True
    )
    architect_id = fields.Many2one(
        'res.partner',
        "Arquitecto / Proyectista"
    )

    # Datos de la obra
    construction_area = fields.Float("Superficie construcción (m²)")
    terrain_area = fields.Float("Superficie terreno (m²)")
    site_address = fields.Text("Dirección de obra")

    # Tipo de proyecto
    project_type = fields.Selection([
        ('admin', 'Administración'),
        ('llave_mano', 'Llave en mano'),
        ('supervision', 'Supervisión'),
        ('remodelacion', 'Remodelación'),
        ('mantenimiento', 'Mantenimiento'),
    ], string="Tipo de proyecto", default='admin', tracking=True)

    # === PRESUPUESTO ===
    budget_line_ids = fields.One2many(
        'sc360.budget.line',
        'project_id',
        "Líneas de presupuesto"
    )
    budget_line_count = fields.Integer(compute='_compute_budget_counts')

    # === REQUISICIONES Y COMPRAS ===
    requisition_ids = fields.One2many(
        'sc360.requisition',
        'project_id',
        "Requisiciones"
    )
    requisition_count = fields.Integer(compute='_compute_requisition_count')

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'sc360_project_id',
        "Órdenes de compra"
    )
    purchase_count = fields.Integer(compute='_compute_purchase_count')

    # === TOTALES CALCULADOS ===
    total_budget = fields.Monetary(
        "Total presupuesto",
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id'
    )
    total_purchased = fields.Monetary(
        "Total comprado",
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id'
    )
    total_received = fields.Monetary(
        "Total recibido",
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id'
    )
    budget_variance = fields.Monetary(
        "Variación",
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id',
        help="Positivo = dentro de presupuesto, Negativo = sobrepasado"
    )
    budget_variance_pct = fields.Float(
        "Variación %",
        compute='_compute_budget_totals',
        store=True,
        digits=(5, 2)
    )
    budget_execution_pct = fields.Float(
        "% Ejecutado",
        compute='_compute_budget_totals',
        store=True,
        digits=(5, 2)
    )

    # Moneda
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    # === COMPUTES ===

    def _compute_budget_counts(self):
        for project in self:
            project.budget_line_count = len(project.budget_line_ids)

    def _compute_requisition_count(self):
        for project in self:
            project.requisition_count = len(project.requisition_ids)

    def _compute_purchase_count(self):
        for project in self:
            project.purchase_count = len(project.purchase_order_ids)

    @api.depends(
        'budget_line_ids.amount_budget',
        'budget_line_ids.amount_purchased',
        'budget_line_ids.amount_received'
    )
    def _compute_budget_totals(self):
        for project in self:
            lines = project.budget_line_ids
            project.total_budget = sum(lines.mapped('amount_budget'))
            project.total_purchased = sum(lines.mapped('amount_purchased'))
            project.total_received = sum(lines.mapped('amount_received'))
            project.budget_variance = project.total_budget - project.total_purchased

            if project.total_budget:
                project.budget_variance_pct = (project.budget_variance / project.total_budget) * 100
                project.budget_execution_pct = (project.total_purchased / project.total_budget) * 100
            else:
                project.budget_variance_pct = 0
                project.budget_execution_pct = 0

    # === ACCIONES ===

    def action_view_budget_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Presupuesto'),
            'res_model': 'sc360.budget.line',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

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

    def action_view_purchases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de compra'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('sc360_project_id', '=', self.id)],
            'context': {'default_sc360_project_id': self.id},
        }

    def action_create_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva requisición'),
            'res_model': 'sc360.requisition',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.id,
                'default_requester_id': self.env.uid,
            },
        }
