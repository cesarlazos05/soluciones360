# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.fields import Command


class Estimate(models.Model):
    """Estimacion semanal de avance de obra vinculada a un contrato."""
    _name = 'sc360.estimate'
    _description = 'Estimacion de avance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'number desc'

    name = fields.Char(
        'Folio', default='Nuevo', copy=False, readonly=True, index=True,
    )
    contract_id = fields.Many2one(
        'sc360.contract', 'Contrato', required=True, tracking=True, index=True,
    )
    project_id = fields.Many2one(
        related='contract_id.project_id', store=True, index=True,
    )
    contractor_id = fields.Many2one(
        related='contract_id.contractor_id', store=True,
    )
    number = fields.Integer('No. Estimacion', readonly=True)
    period_start = fields.Date('Inicio periodo', required=True)
    period_end = fields.Date('Fin periodo', required=True)

    line_ids = fields.One2many(
        'sc360.estimate.line', 'estimate_id', string='Conceptos',
    )

    # --- Totales ---
    subtotal = fields.Float(
        'Subtotal', compute='_compute_totals', store=True, digits='Product Price',
    )
    iva_amount = fields.Float(
        'IVA', compute='_compute_totals', store=True, digits='Product Price',
    )
    total = fields.Float(
        'Total', compute='_compute_totals', store=True, digits='Product Price',
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobada'),
        ('paid', 'Pagada'),
    ], default='draft', tracking=True, string='Estado', index=True)

    contractor_signature = fields.Binary('Firma contratista')
    supervisor_signature = fields.Binary('Firma supervisor')

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('sc360.estimate') or 'Nuevo'
                )
            # Auto-compute estimation number within the contract
            if vals.get('contract_id') and not vals.get('number'):
                existing = self.search([
                    ('contract_id', '=', vals['contract_id']),
                ], order='number desc', limit=1)
                vals['number'] = (existing.number + 1) if existing else 1
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for est in self:
            est.subtotal = sum(est.line_ids.mapped('amount'))
            est.iva_amount = 0.0  # Mano de obra exenta de IVA
            est.total = est.subtotal + est.iva_amount

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_approve(self):
        self.write({'state': 'approved'})
        # Trigger recompute on budget lines
        for est in self:
            budget_lines = est.project_id.partition_ids.mapped('budget_line_ids')
            budget_lines._compute_amount_estimated()

    def action_pay(self):
        self.write({'state': 'paid'})

    def action_draft(self):
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Populate lines from contract
    # ------------------------------------------------------------------

    def action_populate_lines(self):
        """Load lines from contract with accumulated previous from last approved estimation."""
        self.ensure_one()
        self.line_ids.unlink()

        # Find the latest approved/paid estimation for the same contract
        prev = self.env['sc360.estimate'].search([
            ('contract_id', '=', self.contract_id.id),
            ('state', 'in', ['approved', 'paid']),
            ('id', '!=', self.id),
        ], order='number desc', limit=1)

        lines = []
        for cl in self.contract_id.line_ids:
            accum = 0.0
            if prev:
                prev_line = prev.line_ids.filtered(
                    lambda l, _cl=cl: l.contract_line_id.id == _cl.id
                )
                accum = prev_line[0].accum_total if prev_line else 0.0
            lines.append(Command.create({
                'contract_line_id': cl.id,
                'accum_prev': accum,
                'this_estim': 0.0,
            }))
        self.line_ids = lines

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conceptos cargados'),
                'message': _('Se cargaron %d conceptos del contrato.') % len(lines),
                'type': 'success',
                'sticky': False,
            },
        }


class EstimateLine(models.Model):
    """Linea de estimacion: un concepto del contrato con avance de esta semana."""
    _name = 'sc360.estimate.line'
    _description = 'Linea de estimacion'
    _order = 'id'

    estimate_id = fields.Many2one(
        'sc360.estimate', required=True, ondelete='cascade', index=True,
    )

    # --- Referencia al contrato ---
    contract_line_id = fields.Many2one(
        'sc360.contract.line', 'Linea de contrato', required=True,
    )

    # --- Related desde la linea de contrato ---
    concept_name = fields.Char(
        related='contract_line_id.concept_id.name', string='Concepto', store=True,
    )
    uom_id = fields.Many2one(
        related='contract_line_id.uom_id', string='Unidad', store=True,
    )
    unit_price = fields.Float(
        related='contract_line_id.unit_price', string='P.U.', store=True,
    )
    contract_qty = fields.Float(
        related='contract_line_id.quantity', string='Cant. contratada', store=True,
    )

    # --- Acumulados y avance ---
    accum_prev = fields.Float('Acum. Anterior', digits='Product Unit of Measure')
    this_estim = fields.Float('Esta Estimacion', digits='Product Unit of Measure')
    accum_total = fields.Float(
        'Acum. Total', compute='_compute_accum_total', store=True,
        digits='Product Unit of Measure',
    )
    remaining = fields.Float(
        'Restante', compute='_compute_remaining', digits='Product Unit of Measure',
    )
    amount = fields.Float(
        'Importe', compute='_compute_amount', store=True, digits='Product Price',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('accum_prev', 'this_estim')
    def _compute_accum_total(self):
        for line in self:
            line.accum_total = line.accum_prev + line.this_estim

    @api.depends('contract_qty', 'accum_total')
    def _compute_remaining(self):
        for line in self:
            line.remaining = line.contract_qty - line.accum_total

    @api.depends('this_estim', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.this_estim * line.unit_price
