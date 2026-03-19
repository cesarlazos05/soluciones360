# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Requisition(models.Model):
    """Requisición de materiales"""
    _name = 'sc360.requisition'
    _description = 'Requisición de materiales'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'
    _rec_name = 'name'

    # === IDENTIFICACIÓN ===
    name = fields.Char(
        "Folio", 
        default='Nuevo', 
        copy=False, 
        readonly=True,
        index=True
    )
    
    # === FECHAS ===
    date_request = fields.Date(
        "Fecha solicitud", 
        default=fields.Date.today, 
        required=True,
        tracking=True
    )
    date_required = fields.Date(
        "Fecha requerida",
        tracking=True,
        help="Fecha en que se necesitan los materiales en obra"
    )
    
    # === RELACIONES PRINCIPALES ===
    project_id = fields.Many2one(
        'project.project', 
        "Proyecto", 
        required=True, 
        tracking=True,
        index=True,
        domain=[('is_construction_project', '=', True)]
    )
    project_supervisor_id = fields.Many2one(
        related='project_id.supervisor_id',
        string="Supervisor del proyecto",
        store=True
    )
    
    budget_line_id = fields.Many2one(
        'sc360.budget.line', 
        "Partida/Concepto",
        domain="[('project_id', '=', project_id)]",
        tracking=True,
        help="Partida del presupuesto a la que se cargará esta requisición"
    )
    category_id = fields.Many2one(
        related='budget_line_id.category_id', 
        string="Partida",
        store=True
    )
    
    # === SOLICITANTE ===
    requester_id = fields.Many2one(
        'res.users', 
        "Solicitante",
        default=lambda self: self.env.user, 
        required=True,
        tracking=True
    )
    requester_phone = fields.Char("Teléfono solicitante")
    
    # === ESTADO - Flujo simplificado sin aprobaciones ===
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviada a compras'),
        ('in_progress', 'En proceso de compra'),
        ('partial', 'Parcialmente surtida'),
        ('done', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], default='draft', tracking=True, string="Estado", index=True)
    
    # === CONTENIDO ===
    reason = fields.Text(
        "Motivo / Justificación",
        help="Describe por qué se necesitan estos materiales"
    )
    delivery_address = fields.Text(
        "Dirección de entrega",
        help="Dejar vacío para usar la dirección del proyecto"
    )
    
    line_ids = fields.One2many(
        'sc360.requisition.line', 
        'requisition_id', 
        "Materiales",
        copy=True
    )
    line_count = fields.Integer(compute='_compute_line_count')
    
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'sc360_requisition_attachment_rel',
        'requisition_id',
        'attachment_id',
        string="Evidencias / Archivos adjuntos"
    )
    
    # === RELACIÓN CON ODCs GENERADAS ===
    purchase_order_ids = fields.One2many(
        'purchase.order', 
        'sc360_requisition_id',
        "Órdenes de compra"
    )
    purchase_count = fields.Integer(compute='_compute_purchase_count')
    
    # === TOTALES ===
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id
    )
    amount_total_estimated = fields.Monetary(
        "Total estimado",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    amount_total_purchased = fields.Monetary(
        "Total en ODC",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    
    # === CAMPOS ADICIONALES ===
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgente'),
        ('2', 'Muy urgente'),
    ], default='0', string="Prioridad")
    
    notes = fields.Text("Notas internas")
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )

    # === MÉTODOS DE CREACIÓN ===
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('sc360.requisition') or 'Nuevo'
        return super().create(vals_list)

    # === COMPUTES ===
    
    def _compute_line_count(self):
        for req in self:
            req.line_count = len(req.line_ids)

    def _compute_purchase_count(self):
        for req in self:
            req.purchase_count = len(req.purchase_order_ids)

    @api.depends('line_ids.subtotal', 'purchase_order_ids.amount_untaxed', 'purchase_order_ids.state')
    def _compute_totals(self):
        for req in self:
            req.amount_total_estimated = sum(req.line_ids.mapped('subtotal'))
            confirmed_pos = req.purchase_order_ids.filtered(
                lambda po: po.state in ('purchase', 'done')
            )
            req.amount_total_purchased = sum(confirmed_pos.mapped('amount_untaxed'))

    # === ACCIONES DE FLUJO ===
    
    def action_send_to_purchase(self):
        """Envía la requisición al área de compras"""
        for req in self:
            if not req.line_ids:
                raise UserError(_('Debe agregar al menos un material a la requisición.'))
        self.write({'state': 'sent'})
        
        # Crear actividad para el equipo de compras (opcional)
        # self._create_purchase_activity()
        
        return True

    def action_set_draft(self):
        """Regresa a borrador"""
        self.write({'state': 'draft'})
        return True

    def action_cancel(self):
        """Cancela la requisición"""
        for req in self:
            # Verificar si hay ODCs confirmadas
            confirmed_pos = req.purchase_order_ids.filtered(
                lambda po: po.state in ('purchase', 'done')
            )
            if confirmed_pos:
                raise UserError(_(
                    'No puede cancelar esta requisición porque tiene órdenes de compra confirmadas. '
                    'Primero cancele las ODCs: %s'
                ) % ', '.join(confirmed_pos.mapped('name')))
        
        # Cancelar ODCs en borrador
        draft_pos = self.purchase_order_ids.filtered(lambda po: po.state in ('draft', 'sent'))
        draft_pos.button_cancel()
        
        self.write({'state': 'cancelled'})
        return True

    def action_create_purchase_orders(self):
        """Abre wizard para generar ODCs por proveedor"""
        self.ensure_one()
        if self.state not in ('sent', 'in_progress', 'partial'):
            raise UserError(_('Solo puede crear ODCs desde requisiciones enviadas a compras.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generar órdenes de compra'),
            'res_model': 'sc360.generate.purchase.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }

    def action_view_purchases(self):
        """Ver ODCs generadas desde esta requisición"""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de compra'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('sc360_requisition_id', '=', self.id)],
            'context': {'default_sc360_requisition_id': self.id},
        }
        if self.purchase_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.purchase_order_ids[0].id
        return action

    # === MÉTODOS DE ACTUALIZACIÓN DE ESTADO ===
    
    def _update_state_from_purchases(self):
        """Actualiza el estado basado en las ODCs"""
        for req in self:
            if req.state in ('draft', 'cancelled'):
                continue
            
            if not req.purchase_order_ids:
                continue
            
            # Verificar estado de las ODCs
            all_done = all(po.state == 'done' for po in req.purchase_order_ids)
            any_purchase = any(po.state in ('purchase', 'done') for po in req.purchase_order_ids)
            
            # Verificar si todas las líneas están cubiertas
            all_lines_covered = all(
                line.qty_purchased >= line.qty 
                for line in req.line_ids
            )
            
            if all_done and all_lines_covered:
                req.state = 'done'
            elif any_purchase:
                if all_lines_covered:
                    req.state = 'in_progress'
                else:
                    req.state = 'partial'


class RequisitionLine(models.Model):
    """Línea de requisición"""
    _name = 'sc360.requisition.line'
    _description = 'Línea de requisición'
    _order = 'sequence, id'

    requisition_id = fields.Many2one(
        'sc360.requisition', 
        required=True, 
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(default=10)
    
    # === PRODUCTO/MATERIAL ===
    product_id = fields.Many2one(
        'product.product', 
        "Producto/Material",
        domain=[('purchase_ok', '=', True)]
    )
    description = fields.Char("Descripción", required=True)
    
    # === CANTIDADES ===
    qty = fields.Float(
        "Cantidad solicitada", 
        default=1.0, 
        required=True,
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one('uom.uom', "Unidad")
    
    # === PROVEEDOR SUGERIDO (opcional) ===
    suggested_vendor_id = fields.Many2one(
        'res.partner', 
        "Proveedor sugerido",
        domain=[('supplier_rank', '>', 0)],
        help="El área de compras puede cambiarlo"
    )
    
    # === PRECIO ESTIMADO (para referencia) ===
    estimated_price = fields.Float(
        "Precio estimado",
        digits='Product Price'
    )
    currency_id = fields.Many2one(
        related='requisition_id.currency_id'
    )
    subtotal = fields.Monetary(
        "Subtotal estimado",
        compute='_compute_subtotal', 
        store=True,
        currency_field='currency_id'
    )
    
    # === TRACKING DE LO COMPRADO ===
    qty_purchased = fields.Float(
        "Cantidad en ODC", 
        compute='_compute_purchased',
        store=True,
        digits='Product Unit of Measure'
    )
    qty_pending = fields.Float(
        "Cantidad pendiente",
        compute='_compute_purchased',
        store=True,
        digits='Product Unit of Measure'
    )
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 
        'sc360_requisition_line_id',
        "Líneas de ODC"
    )
    
    # === ESTADO ===
    line_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial', 'Parcial'),
        ('complete', 'Completo'),
    ], compute='_compute_purchased', store=True)
    
    # === CAMPOS ADICIONALES ===
    notes = fields.Char("Notas")

    # === CONSTRAINTS ===
    
    @api.constrains('qty')
    def _check_qty(self):
        for line in self:
            if line.qty <= 0:
                raise ValidationError(_('La cantidad debe ser mayor a cero.'))

    # === COMPUTES ===
    
    @api.depends('qty', 'estimated_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.estimated_price

    @api.depends('purchase_line_ids.product_qty', 'purchase_line_ids.order_id.state', 'qty')
    def _compute_purchased(self):
        for line in self:
            # Solo contar líneas de ODCs no canceladas
            valid_po_lines = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state != 'cancel'
            )
            line.qty_purchased = sum(valid_po_lines.mapped('product_qty'))
            line.qty_pending = max(0, line.qty - line.qty_purchased)
            
            # Determinar estado
            if line.qty_purchased >= line.qty:
                line.line_status = 'complete'
            elif line.qty_purchased > 0:
                line.line_status = 'partial'
            else:
                line.line_status = 'pending'

    # === ONCHANGE ===
    
    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_po_id or self.product_id.uom_id
            
            # Buscar último precio de compra
            last_price = self.env['purchase.order.line'].search([
                ('product_id', '=', self.product_id.id),
                ('order_id.state', 'in', ('purchase', 'done'))
            ], order='create_date desc', limit=1)
            
            if last_price:
                self.estimated_price = last_price.price_unit
            elif self.product_id.standard_price:
                self.estimated_price = self.product_id.standard_price
            
            # Buscar proveedor preferido
            seller = self.product_id._select_seller(quantity=self.qty)
            if seller:
                self.suggested_vendor_id = seller.partner_id
