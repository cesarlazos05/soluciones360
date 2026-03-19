from odoo import models, fields, api
from odoo.exceptions import UserError


class GeneratePurchaseWizard(models.TransientModel):
    """Wizard para generar ODCs desde requisición, agrupando por proveedor"""
    _name = 'sc360.generate.purchase.wizard'
    _description = 'Generar órdenes de compra desde requisición'

    requisition_id = fields.Many2one(
        'sc360.requisition', 
        string="Requisición",
        required=True,
        readonly=True
    )
    project_id = fields.Many2one(
        related='requisition_id.project_id',
        string="Proyecto"
    )
    budget_line_id = fields.Many2one(
        related='requisition_id.budget_line_id',
        string="Partida"
    )
    
    line_ids = fields.One2many(
        'sc360.generate.purchase.wizard.line', 
        'wizard_id',
        string="Líneas"
    )
    
    # Resumen
    vendor_count = fields.Integer(
        "Proveedores",
        compute='_compute_summary'
    )
    total_amount = fields.Float(
        "Total estimado",
        compute='_compute_summary'
    )
    currency_id = fields.Many2one(
        related='requisition_id.currency_id'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        if self._context.get('default_requisition_id'):
            req = self.env['sc360.requisition'].browse(
                self._context['default_requisition_id']
            )
            
            lines = []
            for req_line in req.line_ids:
                # Solo incluir líneas con cantidad pendiente
                qty_pending = req_line.qty - req_line.qty_purchased
                if qty_pending <= 0:
                    continue
                    
                lines.append((0, 0, {
                    'requisition_line_id': req_line.id,
                    'product_id': req_line.product_id.id,
                    'description': req_line.description,
                    'qty_requested': req_line.qty,
                    'qty_already_purchased': req_line.qty_purchased,
                    'qty': qty_pending,
                    'uom_id': req_line.uom_id.id,
                    'vendor_id': req_line.suggested_vendor_id.id,
                    'price_unit': req_line.estimated_price,
                }))
            
            res['line_ids'] = lines
            
        return res

    @api.depends('line_ids.vendor_id', 'line_ids.subtotal', 'line_ids.include')
    def _compute_summary(self):
        for wizard in self:
            included_lines = wizard.line_ids.filtered(lambda l: l.include and l.vendor_id)
            wizard.vendor_count = len(set(included_lines.mapped('vendor_id').ids))
            wizard.total_amount = sum(included_lines.mapped('subtotal'))

    def action_generate(self):
        """Genera ODCs agrupadas por proveedor"""
        self.ensure_one()
        req = self.requisition_id
        
        # Filtrar líneas incluidas y con proveedor
        lines_to_process = self.line_ids.filtered(
            lambda l: l.include and l.qty > 0 and l.vendor_id
        )
        
        if not lines_to_process:
            raise UserError(
                "Debe incluir al menos una línea con proveedor asignado.\n\n"
                "Marque la casilla 'Incluir' y asigne un proveedor a las líneas que desea procesar."
            )
        
        # Agrupar líneas por proveedor
        lines_by_vendor = {}
        for line in lines_to_process:
            vendor = line.vendor_id
            if vendor not in lines_by_vendor:
                lines_by_vendor[vendor] = []
            lines_by_vendor[vendor].append(line)
        
        created_pos = self.env['purchase.order']
        
        for vendor, lines in lines_by_vendor.items():
            # Crear ODC para este proveedor
            po_vals = {
                'partner_id': vendor.id,
                'sc360_project_id': req.project_id.id,
                'sc360_budget_line_id': req.budget_line_id.id if req.budget_line_id else False,
                'sc360_requisition_id': req.id,
                'origin': req.name,
                'order_line': [],
            }
            
            for line in lines:
                po_line_vals = {
                    'product_id': line.product_id.id if line.product_id else False,
                    'name': line.description,
                    'product_qty': line.qty,
                    'product_uom': line.uom_id.id if line.uom_id else False,
                    'price_unit': line.price_unit,
                    'sc360_budget_line_id': req.budget_line_id.id if req.budget_line_id else False,
                    'sc360_requisition_line_id': line.requisition_line_id.id,
                }
                po_vals['order_line'].append((0, 0, po_line_vals))
            
            po = self.env['purchase.order'].create(po_vals)
            created_pos |= po
        
        # Actualizar estado de requisición
        if req.state == 'sent':
            req.write({'state': 'in_progress'})
        
        # Mostrar ODCs creadas
        if len(created_pos) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orden de compra',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': created_pos.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': f'Órdenes de compra generadas ({len(created_pos)})',
                'res_model': 'purchase.order',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_pos.ids)],
            }


class GeneratePurchaseWizardLine(models.TransientModel):
    """Línea del wizard para generar compras"""
    _name = 'sc360.generate.purchase.wizard.line'
    _description = 'Línea de wizard generar compra'

    wizard_id = fields.Many2one(
        'sc360.generate.purchase.wizard', 
        ondelete='cascade',
        required=True
    )
    requisition_line_id = fields.Many2one(
        'sc360.requisition.line',
        string="Línea requisición"
    )
    
    include = fields.Boolean("Incluir", default=True)
    
    product_id = fields.Many2one('product.product', string="Producto")
    description = fields.Char("Descripción", required=True)
    
    qty_requested = fields.Float(
        "Solicitado",
        digits='Product Unit of Measure',
        readonly=True
    )
    qty_already_purchased = fields.Float(
        "Ya comprado",
        digits='Product Unit of Measure',
        readonly=True
    )
    qty = fields.Float(
        "Cantidad a comprar", 
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one('uom.uom', string="Unidad")
    
    vendor_id = fields.Many2one(
        'res.partner', 
        string="Proveedor",
        domain="[('supplier_rank', '>', 0)]"
    )
    price_unit = fields.Float("Precio unitario", digits='Product Price')
    subtotal = fields.Float(
        "Subtotal",
        compute='_compute_subtotal',
        digits='Product Price'
    )
    
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('qty', 'price_unit', 'include')
    def _compute_subtotal(self):
        for line in self:
            if line.include:
                line.subtotal = line.qty * line.price_unit
            else:
                line.subtotal = 0.0

    @api.onchange('product_id')
    def _onchange_product(self):
        """Busca proveedores y precios del producto"""
        if self.product_id:
            # Buscar proveedor por defecto del producto
            seller = self.product_id.seller_ids[:1]
            if seller and not self.vendor_id:
                self.vendor_id = seller.partner_id
                self.price_unit = seller.price
            
            if not self.uom_id:
                self.uom_id = self.product_id.uom_po_id or self.product_id.uom_id
