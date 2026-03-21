# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ConceptCategory(models.Model):
    """Partidas del catálogo (ej: PRELIMINARES, ELÉCTRICO, ALBAÑILERÍA)"""
    _name = 'sc360.concept.category'
    _description = 'Partida de concepto'
    _order = 'sequence, code'
    _rec_name = 'complete_name'

    sequence = fields.Integer(default=10)
    code = fields.Char("Código", required=True, index=True)
    name = fields.Char("Nombre", required=True)
    complete_name = fields.Char(
        "Nombre completo",
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )

    parent_id = fields.Many2one(
        'sc360.concept.category',
        "Partida padre",
        index=True,
        ondelete='cascade'
    )
    child_ids = fields.One2many('sc360.concept.category', 'parent_id', "Sub-partidas")

    concept_ids = fields.One2many('sc360.concept.template', 'category_id', "Conceptos")
    concept_count = fields.Integer(compute='_compute_concept_count', store=True)

    active = fields.Boolean(default=True)
    notes = fields.Text("Notas")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código de partida debe ser único'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('concept_ids')
    def _compute_concept_count(self):
        for rec in self:
            rec.concept_count = len(rec.concept_ids)

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('No puede crear partidas recursivas.'))

    def action_view_concepts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conceptos de obra',
            'res_model': 'sc360.concept.template',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'search_default_category_id': self.id},
        }


class ConceptTemplate(models.Model):
    """Conceptos base del catálogo maestro"""
    _name = 'sc360.concept.template'
    _description = 'Concepto de obra'
    _order = 'category_id, sequence, code'
    _rec_name = 'name'

    sequence = fields.Integer(default=10)
    code = fields.Char("Código", index=True)
    name = fields.Char("Nombre corto", required=True)
    description = fields.Text("Descripción completa")

    category_id = fields.Many2one(
        'sc360.concept.category',
        "Partida",
        required=True,
        index=True,
        ondelete='restrict'
    )
    category_complete_name = fields.Char(
        related='category_id.complete_name',
        string="Partida completa",
        store=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        "Unidad de medida",
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        string="Moneda"
    )

    # Precios de referencia (opcionales)
    base_unit_price = fields.Float("P.U. Base referencia", digits='Product Price')
    includes_labor = fields.Boolean("Incluye mano de obra")
    includes_materials = fields.Boolean("Incluye material", default=True)

    # Insumos típicos
    material_ids = fields.One2many(
        'sc360.concept.material',
        'concept_id',
        "Materiales típicos"
    )
    material_count = fields.Integer(compute='_compute_material_count')

    # IVA
    tax_included = fields.Boolean("Precio incluye IVA", default=False)

    active = fields.Boolean(default=True)
    notes = fields.Text("Notas técnicas")

    # Para búsqueda rápida
    search_keywords = fields.Char("Palabras clave", help="Palabras adicionales para búsqueda")

    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_ids)

    def action_view_materials(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Materiales típicos',
            'res_model': 'sc360.concept.material',
            'view_mode': 'list,form',
            'domain': [('concept_id', '=', self.id)],
            'context': {'default_concept_id': self.id},
        }

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Búsqueda mejorada por código, nombre o palabras clave"""
        domain = domain or []
        if name:
            domain = ['|', '|', '|',
                ('code', operator, name),
                ('name', operator, name),
                ('description', operator, name),
                ('search_keywords', operator, name),
            ] + domain
        return self._search(domain, limit=limit, order=order)


class ConceptMaterial(models.Model):
    """Materiales típicos asociados a un concepto"""
    _name = 'sc360.concept.material'
    _description = 'Material típico de concepto'
    _order = 'sequence, id'
    _rec_name = 'description'

    sequence = fields.Integer(default=10)
    concept_id = fields.Many2one(
        'sc360.concept.template',
        required=True,
        ondelete='cascade',
        index=True
    )

    product_id = fields.Many2one(
        'product.product',
        "Producto",
        domain=[('purchase_ok', '=', True)]
    )
    description = fields.Char(
        "Nombre material",
        help="Usar si no hay producto definido en el sistema"
    )

    qty_per_unit = fields.Float(
        "Cantidad por unidad",
        default=1.0,
        digits='Product Unit of Measure',
        help="Cantidad de este material por cada unidad del concepto"
    )
    uom_id = fields.Many2one('uom.uom', "UdM")

    is_optional = fields.Boolean("Opcional")
    is_labor = fields.Boolean("Es mano de obra")
    notes = fields.Char("Notas")

    # Precio de referencia
    unit_price = fields.Float("Precio referencia", digits='Product Price')
    currency_id = fields.Many2one(
        related='concept_id.currency_id',
        store=True,
        string="Moneda"
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id
            if self.product_id.standard_price:
                self.unit_price = self.product_id.standard_price
