# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Requisition(models.Model):
    """Requisicion de materiales con flujo de aprobacion."""
    _name = 'sc360.requisition'
    _description = 'Requisicion de materiales'
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
    concept_id = fields.Many2one(
        'sc360.concept.template', 'Concepto', tracking=True,
    )
    requester_id = fields.Many2one(
        'res.users', 'Solicitante', default=lambda self: self.env.user,
    )
    approver_id = fields.Many2one('res.users', 'Aprobador')
    date_required = fields.Date('Fecha Requerida')
    line_ids = fields.One2many(
        'sc360.requisition.line', 'requisition_id', string='Materiales', copy=True,
    )
    photo_ids = fields.Many2many(
        'ir.attachment',
        'sc360_requisition_photo_rel', 'requisition_id', 'attachment_id',
        string='Evidencias',
    )
    purchase_order_ids = fields.One2many(
        'purchase.order', 'sc360_requisition_id', string='Ordenes de compra',
    )
    purchase_count = fields.Integer(compute='_compute_purchase_count')
    notes = fields.Text('Notas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('approved', 'Aprobada'),
        ('in_purchase', 'En compra'),
        ('done', 'Completada'),
    ], default='draft', tracking=True, string='Estado', index=True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        approver = self.env['ir.config_parameter'].sudo().get_param(
            'sc360.default_approver_id', default=False,
        )
        if approver:
            res['approver_id'] = int(approver)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('sc360.requisition') or 'Nuevo'
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    def _compute_purchase_count(self):
        for req in self:
            req.purchase_count = len(req.purchase_order_ids)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_send(self):
        for req in self:
            if not req.line_ids:
                raise UserError(_('Debe agregar al menos un material.'))
        self.write({'state': 'sent'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'draft'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_create_purchase_orders(self):
        """Open the generate-purchase wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generar ordenes de compra'),
            'res_model': 'sc360.generate.purchase.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }

    def action_view_purchases(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Ordenes de compra'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('sc360_requisition_id', '=', self.id)],
        }
        if self.purchase_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.purchase_order_ids[0].id
        return action


class RequisitionLine(models.Model):
    """Linea de requisicion de materiales."""
    _name = 'sc360.requisition.line'
    _description = 'Linea de requisicion'
    _order = 'id'

    requisition_id = fields.Many2one(
        'sc360.requisition', required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', 'Producto', required=True,
        domain=[('purchase_ok', '=', True)],
    )
    description = fields.Char('Descripcion')
    quantity = fields.Float('Cantidad', required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', 'Unidad', required=True)

    # --- Tracking de lo comprado ---
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'sc360_requisition_line_id', string='Lineas de ODC',
    )
    qty_purchased = fields.Float(
        'Cantidad comprada', compute='_compute_purchased', store=True,
        digits='Product Unit of Measure',
    )
    qty_remaining = fields.Float(
        'Cantidad pendiente', compute='_compute_purchased', store=True,
        digits='Product Unit of Measure',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('purchase_line_ids.product_qty', 'purchase_line_ids.order_id.state', 'quantity')
    def _compute_purchased(self):
        for line in self:
            valid = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state != 'cancel'
            )
            line.qty_purchased = sum(valid.mapped('product_qty'))
            line.qty_remaining = max(0.0, line.quantity - line.qty_purchased)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
