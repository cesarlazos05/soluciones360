# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ConceptCategory(models.Model):
    """Partida del catalogo maestro (ej: PRELIMINARES, ELECTRICO, ALBANILERIA)."""
    _name = 'sc360.concept.category'
    _description = 'Partida de concepto'
    _order = 'code, name'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Codigo', index=True)
    description = fields.Text('Descripcion')
    concept_ids = fields.One2many(
        'sc360.concept.template', 'category_id', string='Conceptos',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El codigo de partida debe ser unico.'),
    ]


class ConceptTemplate(models.Model):
    """Concepto de obra dentro de una partida."""
    _name = 'sc360.concept.template'
    _description = 'Concepto de obra'
    _order = 'code, name'

    category_id = fields.Many2one(
        'sc360.concept.category', 'Partida',
        required=True, index=True, ondelete='restrict',
    )
    name = fields.Char('Nombre', required=True)
    code = fields.Char('Codigo', index=True)
    uom_id = fields.Many2one(
        'uom.uom', 'Unidad de medida', required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    default_price = fields.Float('P.U. de referencia', digits='Product Price')
    material_ids = fields.One2many(
        'sc360.concept.material', 'concept_id', string='Materiales tipicos',
    )
    active = fields.Boolean(default=True)


class ConceptMaterial(models.Model):
    """Material tipico asociado a un concepto de obra."""
    _name = 'sc360.concept.material'
    _description = 'Material tipico de concepto'

    concept_id = fields.Many2one(
        'sc360.concept.template', required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', 'Producto', required=True,
        domain=[('purchase_ok', '=', True)],
    )
    quantity = fields.Float('Cantidad', default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', 'UdM')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
