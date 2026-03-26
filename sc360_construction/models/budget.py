# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.fields import Command


class ProjectPartition(models.Model):
    """Partida asignada a un proyecto especifico."""
    _name = 'sc360.project.partition'
    _description = 'Partida de proyecto'
    _order = 'category_id'

    project_id = fields.Many2one(
        'project.project', 'Proyecto', required=True, ondelete='cascade', index=True,
    )
    category_id = fields.Many2one(
        'sc360.concept.category', 'Partida', required=True,
    )
    budget_line_ids = fields.One2many(
        'sc360.budget.line', 'project_partition_id', string='Lineas de presupuesto',
    )
    total_budget = fields.Float(
        'Total presupuesto', compute='_compute_total_budget', store=True,
    )

    @api.depends('budget_line_ids.amount_budget')
    def _compute_total_budget(self):
        for partition in self:
            partition.total_budget = sum(partition.budget_line_ids.mapped('amount_budget'))

    def action_load_concepts(self):
        """Crea lineas de presupuesto desde los conceptos del catalogo de la partida.

        Omite conceptos que ya tengan linea en esta partida del proyecto.
        """
        self.ensure_one()
        existing_concept_ids = set(self.budget_line_ids.mapped('concept_id').ids)
        templates = self.category_id.concept_ids.filtered(lambda t: t.id not in existing_concept_ids)
        lines = []
        for tmpl in templates:
            lines.append(Command.create({
                'concept_id': tmpl.id,
                'uom_id': tmpl.uom_id.id,
                'unit_price': tmpl.default_price or 0.0,
            }))
        if lines:
            self.budget_line_ids = lines
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conceptos cargados'),
                'message': _('Se cargaron %d conceptos de la partida.') % len(lines),
                'type': 'success',
                'sticky': False,
            },
        }


class BudgetLine(models.Model):
    """Linea de presupuesto de un proyecto."""
    _name = 'sc360.budget.line'
    _description = 'Linea de presupuesto'
    _order = 'project_partition_id, id'

    project_partition_id = fields.Many2one(
        'sc360.project.partition', 'Partida del proyecto',
        required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(
        related='project_partition_id.project_id', store=True, index=True,
    )
    concept_id = fields.Many2one(
        'sc360.concept.template', 'Concepto', required=True,
    )
    uom_id = fields.Many2one('uom.uom', 'Unidad')
    quantity = fields.Float('Cantidad', digits='Product Unit of Measure')
    unit_price = fields.Float('P.U.', digits='Product Price')

    # --- Importes calculados ---
    amount_budget = fields.Float(
        'Importe presupuesto', compute='_compute_amount_budget', store=True,
        digits='Product Price',
    )
    amount_purchased = fields.Float(
        'Importe comprado', compute='_compute_amount_purchased', store=True,
        digits='Product Price',
    )
    amount_estimated = fields.Float(
        'Importe estimado', compute='_compute_amount_estimated', store=True,
        digits='Product Price',
    )
    variance = fields.Float(
        'Variacion', compute='_compute_variance', digits='Product Price',
    )
    progress_pct = fields.Float(
        '% Avance', compute='_compute_variance', digits=(5, 2),
    )

    # --- Relations for reverse lookups ---
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'sc360_budget_line_id', string='Lineas de compra',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('quantity', 'unit_price')
    def _compute_amount_budget(self):
        for line in self:
            line.amount_budget = line.quantity * line.unit_price

    @api.depends(
        'purchase_line_ids.price_subtotal',
        'purchase_line_ids.order_id.state',
    )
    def _compute_amount_purchased(self):
        for line in self:
            confirmed = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ('purchase', 'done')
            )
            line.amount_purchased = sum(confirmed.mapped('price_subtotal'))

    @api.depends('concept_id')  # recomputed via estimate confirm
    def _compute_amount_estimated(self):
        """Sum from approved/paid estimation lines referencing this budget line's concept."""
        EstimateLine = self.env['sc360.estimate.line']
        for line in self:
            est_lines = EstimateLine.search([
                ('contract_line_id.concept_id', '=', line.concept_id.id),
                ('estimate_id.project_id', '=', line.project_id.id),
                ('estimate_id.state', 'in', ['approved', 'paid']),
            ])
            line.amount_estimated = sum(est_lines.mapped('amount'))

    @api.depends('amount_budget', 'amount_purchased', 'amount_estimated')
    def _compute_variance(self):
        for line in self:
            executed = line.amount_purchased + line.amount_estimated
            line.variance = line.amount_budget - executed
            if line.amount_budget:
                line.progress_pct = executed / line.amount_budget * 100
            else:
                line.progress_pct = 0.0

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        if self.concept_id:
            self.uom_id = self.concept_id.uom_id
            self.unit_price = self.concept_id.default_price or 0.0
