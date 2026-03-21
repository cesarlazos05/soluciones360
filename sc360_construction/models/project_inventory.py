# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    """Extensión de proyecto para construcción con inventario por obra"""
    _inherit = 'project.project'

    # === Campos de ubicación de inventario ===
    location_id = fields.Many2one(
        'stock.location',
        'Ubicación de obra',
        domain=[('usage', '=', 'internal')],
        help='Ubicación de inventario específica para esta obra'
    )
    
    create_location = fields.Boolean(
        'Crear ubicación automática',
        default=True,
        help='Crea automáticamente la ubicación de inventario al crear el proyecto'
    )
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Almacén',
        help='Almacén asociado a esta obra'
    )
    
    # === Campos de inventario (calculados) ===
    stock_value = fields.Monetary(
        'Valor inventario',
        compute='_compute_stock_value',
        store=False,
        currency_field='currency_id',
        help='Valor total del inventario en la ubicación de la obra'
    )
    
    stock_products = fields.Integer(
        'Productos en stock',
        compute='_compute_stock_value',
        store=False,
        help='Número de productos diferentes en inventario'
    )
    
    pending_receptions = fields.Integer(
        'Recepciones pendientes',
        compute='_compute_pending',
        store=False,
        help='Número de recepciones pendientes de procesar'
    )
    
    pending_moves = fields.Integer(
        'Movimientos pendientes',
        compute='_compute_pending',
        store=False,
        help='Número de movimientos pendientes'
    )

    # === Sobrescritura de campos de construcción ===
    is_construction = fields.Boolean(
        'Es proyecto de construcción',
        default=True
    )
    
    # Campos existentes (del módulo base)
    client_id = fields.Many2one(
        'res.partner',
        'Cliente',
        domain=[('is_company', '=', True)]
    )
    
    supervisor_id = fields.Many2one(
        'res.users',
        'Supervisor de obra'
    )
    
    architect_id = fields.Many2one(
        'res.partner',
        'Arquitecto'
    )
    
    construction_area = fields.Float(
        'Superficie construcción (m²)'
    )
    
    terrain_area = fields.Float(
        'Superficie terreno (m²)'
    )
    
    site_address = fields.Text('Dirección de obra')
    
    project_type = fields.Selection([
        ('admin', 'Administración'),
        ('llave_mano', 'Llave en mano'),
        ('supervision', 'Supervisión'),
        ('remodelacion', 'Remodelación'),
        ('mantenimiento', 'Mantenimiento'),
    ], 'Tipo de proyecto')
    
    # === Totales (campos existentes) ===
    total_budget = fields.Monetary(
        'Total presupuesto',
        currency_field='currency_id'
    )
    
    total_purchased = fields.Monetary(
        'Total comprado',
        currency_field='currency_id'
    )
    
    total_received = fields.Monetary(
        'Total recibido',
        currency_field='currency_id'
    )
    
    budget_variance = fields.Monetary(
        'Variación',
        currency_field='currency_id'
    )
    
    budget_variance_pct = fields.Float('Variación %')
    
    budget_execution_pct = fields.Float('% Ejecutado')
    
    # === Relaciones ===
    budget_line_ids = fields.One2many(
        'sc360.budget.line',
        'project_id',
        'Líneas de presupuesto'
    )
    
    estimate_ids = fields.One2many(
        'sc360.estimate',
        'project_id',
        'Estimaciones'
    )
    
    requisition_ids = fields.One2many(
        'sc360.requisition',
        'project_id',
        'Requisiciones'
    )

    # === Métodos de creación ===

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project in projects:
            if project.is_construction and project.create_location:
                project._create_project_location()
        return projects

    def _create_project_location(self):
        """Crea ubicación de inventario automáticamente."""
        self.ensure_one()
        
        if self.location_id:
            return self.location_id
        
        # Buscar almacén de la compañía
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not warehouse:
            # Crear almacén si no existe
            warehouse = self.env['stock.warehouse'].create({
                'name': self.name,
                'code': self.name[:5].upper(),
                'company_id': self.company_id.id,
            })
        
        self.warehouse_id = warehouse.id
        
        # Crear ubicación principal del proyecto
        location = self.env['stock.location'].create({
            'name': self.name,
            'location_id': warehouse.lot_stock_id.id,
            'usage': 'internal',
            'company_id': self.company_id.id,
            'comment': f'Ubicación automática - Obra: {self.name}',
        })
        
        # Crear sub-ubicaciones estándar
        sub_locations = [
            ('Materiales', 'Almacén de materiales'),
            ('Herramientas', 'Herramientas en sitio'),
            ('Desperdicios', 'Material de desperdicio'),
            ('En proceso', 'Material en uso activo'),
        ]
        
        for name, comment in sub_locations:
            self.env['stock.location'].create({
                'name': name,
                'location_id': location.id,
                'usage': 'internal',
                'company_id': self.company_id.id,
                'comment': comment,
            })
        
        self.location_id = location.id
        return location

    # === Computes ===

    def _compute_stock_value(self):
        """Calcula el valor del inventario en la ubicación del proyecto."""
        for project in self:
            if not project.location_id:
                project.stock_value = 0
                project.stock_products = 0
                continue
            
            quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', project.location_id.id),
                ('quantity', '>', 0)
            ])
            
            project.stock_products = len(quants)
            project.stock_value = sum(
                q.quantity * q.product_id.standard_price
                for q in quants
            )

    def _compute_pending(self):
        """Calcula recepciones y movimientos pendientes."""
        for project in self:
            if not project.location_id:
                project.pending_receptions = 0
                project.pending_moves = 0
                continue
            
            # Recepciones pendientes
            pickings = self.env['stock.picking'].search([
                ('location_dest_id', 'child_of', project.location_id.id),
                ('state', 'in', ['assigned', 'confirmed']),
            ])
            project.pending_receptions = len(pickings)
            
            # Movimientos pendientes
            moves = self.env['stock.move'].search([
                ('location_dest_id', 'child_of', project.location_id.id),
                ('state', 'in', ['assigned', 'confirmed', 'waiting']),
            ])
            project.pending_moves = len(moves)

    # === Acciones ===

    def action_view_stock(self):
        """Ver inventario del proyecto."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventario: %s') % self.name,
            'res_model': 'stock.quant',
            'view_mode': 'list,pivot',
            'domain': [('location_id', 'child_of', self.location_id.id)],
            'context': {
                'default_location_id': self.location_id.id,
                'search_default_location_id': self.location_id.id,
            },
        }

    def action_view_receptions(self):
        """Ver recepciones pendientes."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recepciones: %s') % self.name,
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('location_dest_id', 'child_of', self.location_id.id),
                ('state', 'in', ['assigned', 'confirmed']),
            ],
            'context': {
                'default_location_dest_id': self.location_id.id,
                'default_picking_type_id': self.env.ref('stock.picking_type_in').id,
            },
        }

    def action_view_estimates(self):
        """Ver estimaciones del proyecto."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estimaciones'),
            'res_model': 'sc360.estimate',
            'view_mode': 'tree,form,kanban',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_budget(self):
        """Ver presupuesto del proyecto."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Presupuesto'),
            'res_model': 'sc360.budget.line',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_new_estimate(self):
        """Crear nueva estimación."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Estimación'),
            'res_model': 'sc360.estimate',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.id,
                'default_supervisor_id': self.supervisor_id.id,
            },
        }