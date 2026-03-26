# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class Contract(models.Model):
    """Contrato de subcontratista."""
    _name = 'sc360.contract'
    _description = 'Contrato de subcontratista'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        'Folio', default='Nuevo', copy=False, readonly=True, index=True,
    )
    project_id = fields.Many2one(
        'project.project', 'Proyecto', required=True, tracking=True, index=True,
        domain=[('is_construction', '=', True)],
    )
    category_id = fields.Many2one(
        'sc360.concept.category', 'Partida', required=True, tracking=True,
    )
    contractor_id = fields.Many2one(
        'res.partner', 'Contratista', required=True, tracking=True,
        domain="[('supplier_rank', '>', 0)]",
    )
    date_start = fields.Date('Fecha inicio')
    date_end = fields.Date('Fecha fin')

    # --- Totales ---
    amount_total = fields.Float(
        'Monto contrato', compute='_compute_amount_total', store=True,
        digits='Product Price',
    )
    amount_estimated = fields.Float(
        'Monto estimado', compute='_compute_amount_estimated', store=True,
        digits='Product Price',
    )
    amount_remaining = fields.Float(
        'Monto restante', compute='_compute_amount_remaining',
        digits='Product Price',
    )

    # --- Lineas y estimaciones ---
    line_ids = fields.One2many(
        'sc360.contract.line', 'contract_id', string='Conceptos del contrato',
    )
    estimation_ids = fields.One2many(
        'sc360.estimate', 'contract_id', string='Estimaciones',
    )
    estimation_count = fields.Integer(compute='_compute_estimation_count')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('done', 'Finalizado'),
        ('cancel', 'Cancelado'),
    ], default='draft', tracking=True, string='Estado', index=True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('sc360.contract') or 'Nuevo'
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for contract in self:
            contract.amount_total = sum(contract.line_ids.mapped('amount'))

    @api.depends('estimation_ids.total', 'estimation_ids.state')
    def _compute_amount_estimated(self):
        for contract in self:
            approved = contract.estimation_ids.filtered(
                lambda e: e.state in ('approved', 'paid')
            )
            contract.amount_estimated = sum(approved.mapped('total'))

    @api.depends('amount_total', 'amount_estimated')
    def _compute_amount_remaining(self):
        for contract in self:
            contract.amount_remaining = contract.amount_total - contract.amount_estimated

    def _compute_estimation_count(self):
        for contract in self:
            contract.estimation_count = len(contract.estimation_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_activate(self):
        self.write({'state': 'active'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_estimations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estimaciones'),
            'res_model': 'sc360.estimate',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }


class ContractLine(models.Model):
    """Linea de contrato de subcontratista."""
    _name = 'sc360.contract.line'
    _description = 'Linea de contrato'
    _order = 'id'

    contract_id = fields.Many2one(
        'sc360.contract', required=True, ondelete='cascade', index=True,
    )
    concept_id = fields.Many2one(
        'sc360.concept.template', 'Concepto', required=True,
    )
    uom_id = fields.Many2one('uom.uom', 'Unidad', required=True)
    quantity = fields.Float('Cantidad contratada', required=True, digits='Product Unit of Measure')
    unit_price = fields.Float('P.U.', required=True, digits='Product Price')
    amount = fields.Float(
        'Importe', compute='_compute_amount', store=True, digits='Product Price',
    )

    # --- Acumulados desde estimaciones ---
    qty_estimated = fields.Float(
        'Cantidad estimada', compute='_compute_estimated',
        digits='Product Unit of Measure',
    )
    qty_remaining = fields.Float(
        'Cantidad restante', compute='_compute_estimated',
        digits='Product Unit of Measure',
    )

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price

    def _compute_estimated(self):
        EstimateLine = self.env['sc360.estimate.line']
        for line in self:
            est_lines = EstimateLine.search([
                ('contract_line_id', '=', line.id),
                ('estimate_id.state', 'in', ['approved', 'paid']),
            ])
            line.qty_estimated = sum(est_lines.mapped('accum_total'))
            line.qty_remaining = line.quantity - line.qty_estimated

    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        if self.concept_id:
            self.uom_id = self.concept_id.uom_id
            self.unit_price = self.concept_id.default_price or 0.0
