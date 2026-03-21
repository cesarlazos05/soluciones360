# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SC360Dashboard(models.Model):
    """Dashboard ejecutivo con KPIs consolidados"""
    _name = 'sc360.dashboard'
    _description = 'Dashboard Ejecutivo SC360'
    _auto = False  # SQL View
    _order = 'project_id'

    # Dimensiones
    project_id = fields.Many2one(
        'project.project',
        'Obra',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        'Compañía',
        readonly=True
    )
    
    # Presupuesto
    budget_total = fields.Monetary(
        'Presupuesto total',
        readonly=True,
        currency_field='currency_id'
    )
    budget_executed = fields.Monetary(
        'Presupuesto ejercido',
        readonly=True,
        currency_field='currency_id'
    )
    budget_pending = fields.Monetary(
        'Presupuesto pendiente',
        readonly=True,
        currency_field='currency_id'
    )
    budget_execution_pct = fields.Float(
        '% Ejecución',
        readonly=True,
        digits=(5, 2)
    )
    
    # Avance
    progress_qty = fields.Float(
        '% Avance cantidad',
        readonly=True,
        digits=(5, 2)
    )
    progress_amount = fields.Float(
        '% Avance importe',
        readonly=True,
        digits=(5, 2)
    )
    
    # Compras
    purchases_total = fields.Monetary(
        'Total compras',
        readonly=True,
        currency_field='currency_id'
    )
    purchases_received = fields.Monetary(
        'Compras recibidas',
        readonly=True,
        currency_field='currency_id'
    )
    purchases_pending = fields.Monetary(
        'Compras pendientes',
        readonly=True,
        currency_field='currency_id'
    )
    
    # Inventario
    stock_value = fields.Monetary(
        'Valor inventario',
        readonly=True,
        currency_field='currency_id'
    )
    stock_products = fields.Integer(
        'Productos en stock',
        readonly=True
    )
    
    # Variaciones
    variance_amount = fields.Monetary(
        'Variación $',
        readonly=True,
        currency_field='currency_id'
    )
    variance_pct = fields.Float(
        'Variación %',
        readonly=True,
        digits=(5, 2)
    )
    
    # Contadores
    estimate_count = fields.Integer(
        'Número de estimaciones',
        readonly=True
    )
    requisition_count = fields.Integer(
        'Número de requisiciones',
        readonly=True
    )
    purchase_count = fields.Integer(
        'Número de ODCs',
        readonly=True
    )
    
    # Moneda
    currency_id = fields.Many2one(
        related='project_id.currency_id',
        readonly=True
    )
    
    # Estado del proyecto
    project_state = fields.Selection(
        related='project_id.stage_id.name',
        readonly=True
    )
    project_status = fields.Char(
        'Estado',
        readonly=True
    )

    def init(self):
        """Inicializa la vista SQL para el dashboard."""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS sc360_dashboard;
            CREATE OR REPLACE VIEW sc360_dashboard AS (
                SELECT 
                    p.id AS id,
                    p.id AS project_id,
                    p.company_id AS company_id,
                    COALESCE(SUM(bl.amount_budget), 0) AS budget_total,
                    COALESCE(SUM(bl.amount_received), 0) AS budget_executed,
                    COALESCE(SUM(bl.amount_budget - bl.amount_received), 0) AS budget_pending,
                    CASE 
                        WHEN SUM(bl.amount_budget) > 0 
                        THEN ROUND(SUM(bl.amount_received) * 100.0 / NULLIF(SUM(bl.amount_budget), 0), 2)
                        ELSE 0 
                    END AS budget_execution_pct,
                    COALESCE(AVG(bl.progress_qty), 0) AS progress_qty,
                    COALESCE(AVG(bl.progress_amount), 0) AS progress_amount,
                    COALESCE(purchases.total, 0) AS purchases_total,
                    COALESCE(purchases.received, 0) AS purchases_received,
                    COALESCE(purchases.total - purchases.received, 0) AS purchases_pending,
                    COALESCE(stock.value, 0) AS stock_value,
                    COALESCE(stock.products, 0) AS stock_products,
                    COALESCE(SUM(bl.variance), 0) AS variance_amount,
                    CASE 
                        WHEN SUM(bl.amount_budget) > 0 
                        THEN ROUND(SUM(bl.variance) * 100.0 / NULLIF(SUM(bl.amount_budget), 0), 2)
                        ELSE 0 
                    END AS variance_pct,
                    COALESCE(estimates.count, 0) AS estimate_count,
                    COALESCE(requisitions.count, 0) AS requisition_count,
                    COALESCE(purchases.count, 0) AS purchase_count
                FROM project_project p
                LEFT JOIN sc360_budget_line bl ON bl.project_id = p.id AND bl.active = true
                LEFT JOIN LATERAL (
                    SELECT 
                        po.project_id,
                        SUM(po.amount_total) AS total,
                        SUM(CASE WHEN po.state = 'done' THEN po.amount_total ELSE 0 END) AS received,
                        COUNT(po.id) AS count
                    FROM purchase_order po
                    WHERE po.state IN ('purchase', 'done')
                    GROUP BY po.project_id
                ) purchases ON purchases.project_id = p.id
                LEFT JOIN LATERAL (
                    SELECT 
                        sq.location_id,
                        SUM(sq.quantity * pt.standard_price) AS value,
                        COUNT(DISTINCT sq.product_id) AS products
                    FROM stock_quant sq
                    JOIN product_product pp ON pp.id = sq.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE sq.quantity > 0
                    GROUP BY sq.location_id
                ) stock ON stock.location_id = p.location_id
                LEFT JOIN LATERAL (
                    SELECT 
                        e.project_id,
                        COUNT(e.id) AS count
                    FROM sc360_estimate e
                    WHERE e.state IN ('submitted', 'approved', 'paid')
                    GROUP BY e.project_id
                ) estimates ON estimates.project_id = p.id
                LEFT JOIN LATERAL (
                    SELECT 
                        r.project_id,
                        COUNT(r.id) AS count
                    FROM sc360_requisition r
                    WHERE r.state != 'cancelled'
                    GROUP BY r.project_id
                ) requisitions ON requisitions.project_id = p.id
                WHERE p.is_construction = true
                GROUP BY p.id, p.company_id, purchases.total, purchases.received, 
                         purchases.count, stock.value, stock.products, 
                         estimates.count, requisitions.count
            )
        """)

    # === Métodos de acción ===

    def action_view_project(self):
        """Ver proyecto completo."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Obra'),
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
        }

    def action_view_budget(self):
        """Ver presupuesto."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Presupuesto'),
            'res_model': 'sc360.budget.line',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_estimates(self):
        """Ver estimaciones."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estimaciones'),
            'res_model': 'sc360.estimate',
            'view_mode': 'tree,form,kanban',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_purchases(self):
        """Ver órdenes de compra."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de Compra'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('sc360_project_id', '=', self.project_id.id)],
            'context': {'default_sc360_project_id': self.project_id.id},
        }

    def action_view_stock(self):
        """Ver inventario."""
        self.ensure_one()
        return self.project_id.action_view_stock()


class SC360DashboardKPI(models.Model):
    """KPIs calculados para el dashboard"""
    _name = 'sc360.dashboard.kpi'
    _description = 'KPI del Dashboard'
    _auto = False

    name = fields.Char('Nombre', readonly=True)
    value = fields.Float('Valor', readonly=True)
    unit = fields.Char('Unidad', readonly=True)
    project_id = fields.Many2one('project.project', 'Proyecto', readonly=True)
    date = fields.Date('Fecha', readonly=True)

    def init(self):
        """Vista SQL para KPIs agregados."""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS sc360_dashboard_kpi;
            CREATE OR REPLACE VIEW sc360_dashboard_kpi AS (
                SELECT 
                    row_number() OVER () AS id,
                    'budget_total' AS name,
                    SUM(amount_budget) AS value,
                    'MXN' AS unit,
                    project_id,
                    CURRENT_DATE AS date
                FROM sc360_budget_line
                WHERE active = true
                GROUP BY project_id
                
                UNION ALL
                
                SELECT 
                    row_number() OVER () + 1000 AS id,
                    'progress_avg' AS name,
                    AVG(progress_amount) AS value,
                    '%' AS unit,
                    project_id,
                    CURRENT_DATE AS date
                FROM sc360_budget_line
                WHERE active = true
                GROUP BY project_id
            )
        """)