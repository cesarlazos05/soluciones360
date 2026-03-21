# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SC360Dashboard(models.Model):
    """Dashboard ejecutivo con KPIs consolidados - Versión simplificada"""
    _name = 'sc360.dashboard'
    _description = 'Dashboard Ejecutivo SC360'
    _auto = False
    _order = 'project_id'

    project_id = fields.Many2one(
        'project.project',
        'Obra',
        readonly=True
    )
    
    budget_total = fields.Float('Presupuesto total', readonly=True)
    budget_executed = fields.Float('Presupuesto ejecutado', readonly=True)
    budget_execution_pct = fields.Float('% Ejecución', readonly=True)
    progress_amount = fields.Float('% Avance importe', readonly=True)
    variance_pct = fields.Float('Variación %', readonly=True)
    estimate_count = fields.Integer('Estimaciones', readonly=True)
    purchase_count = fields.Integer('Órdenes de compra', readonly=True)

    def init(self):
        """Crea la vista SQL del dashboard."""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS sc360_dashboard;
            CREATE OR REPLACE VIEW sc360_dashboard AS (
                SELECT 
                    p.id AS id,
                    p.id AS project_id,
                    COALESCE(SUM(bl.amount_budget), 0) AS budget_total,
                    COALESCE(SUM(bl.amount_estimated), 0) AS budget_executed,
                    CASE 
                        WHEN SUM(bl.amount_budget) > 0 
                        THEN ROUND(SUM(bl.amount_estimated) * 100.0 / NULLIF(SUM(bl.amount_budget), 0), 2)
                        ELSE 0 
                    END AS budget_execution_pct,
                    COALESCE(AVG(bl.progress_amount), 0) AS progress_amount,
                    CASE 
                        WHEN SUM(bl.amount_budget) > 0 
                        THEN ROUND(SUM(bl.amount_budget - bl.amount_received) * 100.0 / NULLIF(SUM(bl.amount_budget), 0), 2)
                        ELSE 0 
                    END AS variance_pct,
                    COALESCE(estimates.count, 0) AS estimate_count,
                    COALESCE(purchases.count, 0) AS purchase_count
                FROM project_project p
                LEFT JOIN sc360_budget_line bl ON bl.project_id = p.id AND bl.active = true
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS count
                    FROM sc360_estimate e
                    WHERE e.project_id = p.id AND e.state IN ('submitted', 'approved', 'paid')
                ) estimates ON true
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS count
                    FROM purchase_order po
                    WHERE po.sc360_project_id = p.id AND po.state IN ('purchase', 'done')
                ) purchases ON true
                WHERE p.is_construction = true
                GROUP BY p.id, estimates.count, purchases.count
            )
        """)