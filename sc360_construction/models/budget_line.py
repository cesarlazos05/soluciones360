# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetLine(models.Model):
    """Línea de presupuesto de un proyecto específico"""
    _name = 'sc360.budget.line'
    _description = 'Línea de presupuesto'
    _order = 'project_id, category_id, sequence'
    _rec_name = 'name'

    # === RELACIONES PRINCIPALES ===
    project_id = fields.Many2one(
        'project.project',
        "Proyecto",
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer("No.", default=10)

    # Origen del catálogo (opcional, para trazabilidad)
    concept_template_id = fields.Many2one(
        'sc360.concept.template',
        "Concepto origen",
        help="Concepto del catálogo maestro del que se originó esta línea"
    )

    # === DATOS DEL CONCEPTO (editables por proyecto) ===
    category_id = fields.Many2one(
        'sc360.concept.category',
        "Partida",
        required=True,
        index=True
    )
    category_code = fields.Char(related='category_id.code', store=True)

    code = fields.Char("Código")
    name = fields.Char("Concepto", required=True)
    description = fields.Text("Descripción")

    uom_id = fields.Many2one(
        'uom.uom',
        "Unidad",
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
    )

    # === PRESUPUESTO ===
    qty_budget = fields.Float(
        "Cantidad presupuestada",
        default=1.0,
        digits='Product Unit of Measure'
    )
    unit_price = fields.Float(
        "P.U.",
        digits='Product Price'
    )
    amount_budget = fields.Float(
        "Importe presupuesto",
        compute='_compute_amounts',
        store=True,
        digits='Product Price'
    )

    currency_id = fields.Many2one(
        related='project_id.currency_id',
        store=True
    )

    # === T.P.U. (opcional, informativo) ===
    tpu_number = fields.Char("No. T.P.U.")
    tpu_price = fields.Float("$ T.P.U.", digits='Product Price')
    tpu_percentage = fields.Float("% T.P.U.", digits=(5, 2))

    # === EJECUCIÓN (calculado desde compras) ===
    qty_purchased = fields.Float(
        "Cantidad comprada",
        compute='_compute_execution',
        store=True,
        digits='Product Unit of Measure'
    )
    amount_purchased = fields.Float(
        "Importe comprado",
        compute='_compute_execution',
        store=True,
        digits='Product Price'
    )
    qty_received = fields.Float(
        "Cantidad recibida",
        compute='_compute_execution',
        store=True,
        digits='Product Unit of Measure'
    )
    amount_received = fields.Float(
        "Importe recibido",
        compute='_compute_execution',
        store=True,
        digits='Product Price'
    )
    variance = fields.Float(
        "Variación $",
        compute='_compute_execution',
        store=True,
        digits='Product Price',
        help="Positivo = ahorro, Negativo = sobregasto"
    )
    variance_pct = fields.Float(
        "Variación %",
        compute='_compute_execution',
        store=True,
        digits=(5, 2)
    )
    execution_pct = fields.Float(
        "% Ejercido",
        compute='_compute_execution',
        store=True,
        digits=(5, 2)
    )

    # === ESTADO VISUAL ===
    budget_status = fields.Selection([
        ('ok', 'Dentro de presupuesto'),
        ('warning', 'Cerca del límite'),
        ('over', 'Sobrepasado'),
    ], compute='_compute_budget_status', store=True)

    # === RELACIONES ===
    requisition_ids = fields.One2many(
        'sc360.requisition',
        'budget_line_id',
        "Requisiciones"
    )
    requisition_count = fields.Integer(compute='_compute_counts')

    purchase_line_ids = fields.One2many(
        'purchase.order.line',
        'sc360_budget_line_id',
        "Líneas de compra"
    )
    purchase_count = fields.Integer(compute='_compute_counts')

    # === CAMPOS ADICIONALES ===
    active = fields.Boolean(default=True)
    notes = fields.Text("Notas")

    # === CONSTRAINTS ===
    _sql_constraints = [
        ('positive_qty', 'CHECK(qty_budget >= 0)', 'La cantidad presupuestada debe ser positiva'),
        ('positive_price', 'CHECK(unit_price >= 0)', 'El precio unitario debe ser positivo'),
    ]

    # === COMPUTES ===

    @api.depends('qty_budget', 'unit_price')
    def _compute_amounts(self):
        for line in self:
            line.amount_budget = line.qty_budget * line.unit_price

    @api.depends(
        'purchase_line_ids.price_subtotal',
        'purchase_line_ids.product_qty',
        'purchase_line_ids.qty_received',
        'purchase_line_ids.order_id.state',
        'amount_budget',
        'unit_price'
    )
    def _compute_execution(self):
        for line in self:
            confirmed_lines = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ('purchase', 'done')
            )

            line.qty_purchased = sum(confirmed_lines.mapped('product_qty'))
            line.amount_purchased = sum(confirmed_lines.mapped('price_subtotal'))
            line.qty_received = sum(confirmed_lines.mapped('qty_received'))

            if line.qty_purchased and line.amount_purchased:
                avg_price = line.amount_purchased / line.qty_purchased
                line.amount_received = line.qty_received * avg_price
            else:
                line.amount_received = line.qty_received * line.unit_price

            line.variance = line.amount_budget - line.amount_purchased

            if line.amount_budget:
                line.variance_pct = (line.variance / line.amount_budget) * 100
                line.execution_pct = (line.amount_purchased / line.amount_budget) * 100
            else:
                line.variance_pct = 0
                line.execution_pct = 0

    @api.depends('variance_pct', 'execution_pct')
    def _compute_budget_status(self):
        for line in self:
            if line.execution_pct > 100:
                line.budget_status = 'over'
            elif line.execution_pct >= 90:
                line.budget_status = 'warning'
            else:
                line.budget_status = 'ok'

    def _compute_counts(self):
        for line in self:
            line.requisition_count = len(line.requisition_ids)
            line.purchase_count = len(line.purchase_line_ids)

    # === ONCHANGE ===

    @api.onchange('concept_template_id')
    def _onchange_concept_template(self):
        if self.concept_template_id:
            tmpl = self.concept_template_id
            self.category_id = tmpl.category_id
            self.code = tmpl.code
            self.name = tmpl.name
            self.description = tmpl.description
            self.uom_id = tmpl.uom_id
            self.unit_price = tmpl.base_unit_price or 0.0

    # === ACCIONES ===

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requisiciones'),
            'res_model': 'sc360.requisition',
            'view_mode': 'list,form',
            'domain': [('budget_line_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_budget_line_id': self.id,
            },
        }

    def action_view_purchases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Líneas de compra'),
            'res_model': 'purchase.order.line',
            'view_mode': 'list,form',
            'domain': [('sc360_budget_line_id', '=', self.id)],
        }

    def action_create_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva requisición'),
            'res_model': 'sc360.requisition',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.project_id.id,
                'default_budget_line_id': self.id,
                'default_requester_id': self.env.uid,
            },
        }
