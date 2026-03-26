# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sc360_project_id = fields.Many2one(
        'project.project', 'Proyecto SC360', tracking=True, index=True,
    )
    sc360_category_id = fields.Many2one(
        'sc360.concept.category', 'Partida',
    )
    sc360_concept_id = fields.Many2one(
        'sc360.concept.template', 'Concepto',
    )
    sc360_requisition_id = fields.Many2one(
        'sc360.requisition', 'Requisicion', tracking=True,
    )
    sc360_tpu_reference = fields.Float('Precio Presupuestado (TPU)')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sc360_budget_line_id = fields.Many2one(
        'sc360.budget.line', 'Linea de Presupuesto',
    )
    sc360_requisition_line_id = fields.Many2one(
        'sc360.requisition.line', 'Linea de requisicion',
    )
