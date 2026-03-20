# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Vinculación con SC360
    sc360_project_id = fields.Many2one(
        'project.project', 
        string="Proyecto SC360",
        tracking=True,
        index=True
    )
    sc360_budget_line_id = fields.Many2one(
        'sc360.budget.line', 
        string="Partida/Concepto",
        domain="[('project_id', '=', sc360_project_id)]",
        tracking=True
    )
    sc360_requisition_id = fields.Many2one(
        'sc360.requisition', 
        string="Requisición origen",
        tracking=True
    )

    # Campos relacionados
    supervisor_id = fields.Many2one(
        related='sc360_project_id.supervisor_id', 
        store=True,
        string="Supervisor"
    )
    project_client_id = fields.Many2one(
        related='sc360_project_id.client_id',
        string="Cliente del proyecto"
    )
    category_id = fields.Many2one(
        related='sc360_budget_line_id.category_id',
        store=True,
        string="Partida"
    )

    # Campos informativos adicionales
    odc_internal_number = fields.Char("# ODC interno")

    @api.onchange('sc360_requisition_id')
    def _onchange_requisition(self):
        if self.sc360_requisition_id:
            req = self.sc360_requisition_id
            self.sc360_project_id = req.project_id
            self.sc360_budget_line_id = req.budget_line_id

    @api.onchange('sc360_project_id')
    def _onchange_project(self):
        """Limpiar partida si cambia el proyecto"""
        if self.sc360_budget_line_id and self.sc360_budget_line_id.project_id != self.sc360_project_id:
            self.sc360_budget_line_id = False

    def button_confirm(self):
        res = super().button_confirm()
        requisitions = self.mapped('sc360_requisition_id')
        requisitions._update_state_from_purchases()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        requisitions = self.mapped('sc360_requisition_id')
        requisitions._update_state_from_purchases()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Vinculación con presupuesto y requisición
    sc360_budget_line_id = fields.Many2one(
        'sc360.budget.line', 
        string="Partida presupuesto"
    )
    sc360_requisition_line_id = fields.Many2one(
        'sc360.requisition.line', 
        string="Línea requisición origen"
    )

    # T.P.U. informativo
    tpu_price = fields.Float("$ T.P.U.")

    # Campos relacionados para reportes
    project_id = fields.Many2one(
        related='order_id.sc360_project_id',
        store=True,
        string="Proyecto"
    )
    category_id = fields.Many2one(
        related='sc360_budget_line_id.category_id',
        store=True,
        string="Partida"
    )

    @api.onchange('sc360_requisition_line_id')
    def _onchange_requisition_line(self):
        """Copiar datos de la línea de requisición"""
        if self.sc360_requisition_line_id:
            req_line = self.sc360_requisition_line_id
            self.product_id = req_line.product_id
            self.name = req_line.description
            self.product_qty = req_line.qty_pending or req_line.qty
            self.product_uom = req_line.uom_id
            self.price_unit = req_line.estimated_price
            
            if req_line.requisition_id.budget_line_id:
                self.sc360_budget_line_id = req_line.requisition_id.budget_line_id
