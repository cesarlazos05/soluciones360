# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GeneratePurchaseWizard(models.TransientModel):
    """Wizard para generar ordenes de compra desde una requisicion, agrupando por proveedor."""
    _name = 'sc360.generate.purchase.wizard'
    _description = 'Generar ordenes de compra desde requisicion'

    requisition_id = fields.Many2one(
        'sc360.requisition', 'Requisicion', required=True, readonly=True,
    )
    line_ids = fields.One2many(
        'sc360.generate.purchase.wizard.line', 'wizard_id', string='Lineas',
    )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        req_id = self._context.get('default_requisition_id')
        if req_id:
            req = self.env['sc360.requisition'].browse(req_id)
            lines = []
            for rl in req.line_ids:
                if rl.qty_remaining <= 0:
                    continue
                lines.append((0, 0, {
                    'requisition_line_id': rl.id,
                    'product_id': rl.product_id.id,
                    'description': rl.description or rl.product_id.display_name,
                    'quantity': rl.qty_remaining,
                    'uom_id': rl.uom_id.id,
                    'partner_id': False,
                    'price_unit': 0.0,
                }))
            res['line_ids'] = lines
        return res

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_generate(self):
        """Generate purchase orders grouped by partner."""
        self.ensure_one()
        req = self.requisition_id

        lines_with_partner = self.line_ids.filtered(
            lambda l: l.partner_id and l.quantity > 0
        )
        if not lines_with_partner:
            raise UserError(_(
                'Debe asignar un proveedor y cantidad a al menos una linea.'
            ))

        # Group by partner
        lines_by_partner = {}
        for wl in lines_with_partner:
            partner = wl.partner_id
            lines_by_partner.setdefault(partner, self.env['sc360.generate.purchase.wizard.line'])
            lines_by_partner[partner] |= wl

        created_pos = self.env['purchase.order']

        for partner, wlines in lines_by_partner.items():
            po_vals = {
                'partner_id': partner.id,
                'sc360_project_id': req.project_id.id,
                'sc360_category_id': req.category_id.id if req.category_id else False,
                'sc360_concept_id': req.concept_id.id if req.concept_id else False,
                'sc360_requisition_id': req.id,
                'sc360_tpu_reference': self._get_tpu_reference(req),
                'origin': req.name,
                'order_line': [],
            }
            for wl in wlines:
                po_vals['order_line'].append((0, 0, {
                    'product_id': wl.product_id.id if wl.product_id else False,
                    'name': wl.description or '/',
                    'product_uom_qty': wl.quantity,
                    'product_uom_id': wl.uom_id.id if wl.uom_id else False,
                    'price_unit': wl.price_unit,
                    'sc360_requisition_line_id': wl.requisition_line_id.id,
                }))
            po = self.env['purchase.order'].create(po_vals)
            created_pos |= po

        # Move requisition to in_purchase
        req.write({'state': 'in_purchase'})

        # Return action to view created PO(s)
        if len(created_pos) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Orden de compra'),
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': created_pos.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordenes de compra generadas'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pos.ids)],
        }


    def _get_tpu_reference(self, req):
        """Load TPU reference from budget for this requisition's partition."""
        if req.project_id and req.category_id:
            partition = self.env['sc360.project.partition'].search([
                ('project_id', '=', req.project_id.id),
                ('category_id', '=', req.category_id.id),
            ], limit=1)
            if partition and partition.total_budget:
                return partition.total_budget
        return 0.0


class GeneratePurchaseWizardLine(models.TransientModel):
    """Linea del wizard para generar ordenes de compra."""
    _name = 'sc360.generate.purchase.wizard.line'
    _description = 'Linea de wizard generar compra'

    wizard_id = fields.Many2one(
        'sc360.generate.purchase.wizard', ondelete='cascade', required=True,
    )
    requisition_line_id = fields.Many2one(
        'sc360.requisition.line', 'Linea de requisicion',
    )
    product_id = fields.Many2one(
        related='requisition_line_id.product_id', string='Producto',
    )
    description = fields.Char('Descripcion')
    quantity = fields.Float('Cantidad', digits='Product Unit of Measure')
    uom_id = fields.Many2one(
        related='requisition_line_id.uom_id', string='Unidad',
    )
    partner_id = fields.Many2one(
        'res.partner', 'Proveedor', required=True,
        domain="[('supplier_rank', '>', 0)]",
    )
    price_unit = fields.Float('P.U.', digits='Product Price')
