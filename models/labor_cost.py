# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SC360LaborCost(models.Model):
    """Costos de mano de obra por concepto"""
    _name = 'sc360.labor.cost'
    _description = 'Costo de Mano de Obra'
    _order = 'estimate_id, budget_line_id, date'

    # Relaciones
    estimate_id = fields.Many2one(
        'sc360.estimate',
        'Estimación',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    budget_line_id = fields.Many2one(
        'sc360.budget.line',
        'Concepto',
        required=True,
        domain="[('project_id', '=', parent.project_id)]"
    )
    
    # Datos del concepto (related)
    concept_code = fields.Char(
        related='budget_line_id.code',
        string='Código',
        readonly=True,
        store=True
    )
    concept_name = fields.Char(
        related='budget_line_id.name',
        string='Concepto',
        readonly=True,
        store=True
    )
    
    # Tipo de trabajador
    worker_type = fields.Selection([
        ('helper', 'Ayudante'),
        ('skilled', 'Oficial'),
        ('master', 'Maistro'),
        ('specialist', 'Especialista'),
    ], 'Tipo de trabajador', required=True, default='helper')
    
    # Horas y tarifas
    hours = fields.Float(
        'Horas trabajadas',
        required=True,
        digits='Product Unit of Measure',
        default=0.0
    )
    
    hourly_rate = fields.Monetary(
        'Tarifa por hora',
        required=True,
        currency_field='currency_id'
    )
    
    amount = fields.Monetary(
        'Costo total',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id'
    )
    
    # Fecha
    date = fields.Date(
        'Fecha',
        default=fields.Date.today,
        required=True
    )
    
    # Notas
    notes = fields.Text('Observaciones')
    
    # Trabajador (opcional)
    worker_id = fields.Many2one(
        'hr.employee',
        'Trabajador',
        help='Trabajador específico (opcional)'
    )
    
    # Moneda
    currency_id = fields.Many2one(
        related='estimate_id.currency_id',
        store=True
    )
    
    # Constraints
    _sql_constraints = [
        ('hours_positive', 'CHECK(hours >= 0)', 'Las horas deben ser positivas.'),
        ('rate_positive', 'CHECK(hourly_rate >= 0)', 'La tarifa debe ser positiva.'),
    ]
    
    @api.depends('hours', 'hourly_rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.hours * line.hourly_rate

    @api.onchange('worker_type')
    def _onchange_worker_type(self):
        """Carga tarifa por defecto según tipo de trabajador."""
        # Tarifas por defecto (pueden configurarse)
        default_rates = {
            'helper': 150.0,
            'skilled': 200.0,
            'master': 300.0,
            'specialist': 400.0,
        }
        if self.worker_type:
            self.hourly_rate = default_rates.get(self.worker_type, 0.0)


class SC360IndirectCost(models.Model):
    """Costos indirectos del proyecto"""
    _name = 'sc360.indirect.cost'
    _description = 'Costo Indirecto'
    _order = 'project_id, sequence'

    # Relaciones
    project_id = fields.Many2one(
        'project.project',
        'Proyecto',
        required=True,
        domain=[('is_construction', '=', True)],
        index=True
    )
    
    sequence = fields.Integer('No.', default=10)
    
    # Datos
    name = fields.Char('Descripción', required=True)
    
    cost_type = fields.Selection([
        ('architect', 'Arquitecto'),
        ('engineer', 'Ingeniero'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Administrativo'),
        ('equipment', 'Equipos'),
        ('utilities', 'Servicios'),
        ('insurance', 'Seguros'),
        ('other', 'Otros'),
    ], 'Tipo de costo', required=True, default='admin')
    
    # Cálculo
    calculation_type = fields.Selection([
        ('fixed', 'Monto fijo'),
        ('percentage', 'Porcentaje del presupuesto'),
        ('prorrate', 'Prorrateo por concepto'),
    ], 'Tipo de cálculo', required=True, default='fixed')
    
    # Montos
    amount = fields.Monetary(
        'Monto',
        currency_field='currency_id',
        digits='Product Price'
    )
    
    percentage = fields.Float(
        'Porcentaje',
        digits=(5, 2),
        help='Porcentaje sobre el presupuesto total'
    )
    
    # Distribución
    distributed_amount = fields.Monetary(
        'Monto distribuido',
        compute='_compute_distributed',
        store=True,
        currency_field='currency_id'
    )
    
    distribution_line_ids = fields.One2many(
        'sc360.indirect.cost.line',
        'indirect_cost_id',
        'Distribución'
    )
    
    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
    ], default='draft', string='Estado')
    
    # Moneda
    currency_id = fields.Many2one(
        related='project_id.currency_id',
        store=True
    )
    
    # Notes
    notes = fields.Text('Notas')

    @api.depends('amount', 'percentage', 'calculation_type', 'project_id.total_budget')
    def _compute_distributed(self):
        for cost in self:
            if cost.calculation_type == 'fixed':
                cost.distributed_amount = cost.amount
            elif cost.calculation_type == 'percentage':
                if cost.project_id and cost.project_id.total_budget:
                    cost.distributed_amount = cost.project_id.total_budget * (cost.percentage / 100)
                else:
                    cost.distributed_amount = 0
            else:
                cost.distributed_amount = cost.amount

    def action_confirm(self):
        """Confirma el costo indirecto."""
        self.write({'state': 'confirmed'})
        
        if self.calculation_type == 'prorrate':
            self._prorrate_indirect_cost()
        
        return True

    def _prorrate_indirect_cost(self):
        """Distribuye el costo indirecto proporcionalmente."""
        self.ensure_one()
        
        if not self.project_id:
            return
        
        # Obtener líneas de presupuesto activas
        budget_lines = self.env['sc360.budget.line'].search([
            ('project_id', '=', self.project_id.id),
            ('active', '=', True)
        ])
        
        if not budget_lines:
            return
        
        total_budget = sum(budget_lines.mapped('amount_budget'))
        
        if total_budget == 0:
            return
        
        # Crear líneas de distribución
        lines_to_create = []
        for line in budget_lines:
            proportion = line.amount_budget / total_budget
            distributed = self.distributed_amount * proportion
            
            if distributed > 0:
                lines_to_create.append({
                    'indirect_cost_id': self.id,
                    'budget_line_id': line.id,
                    'amount': distributed,
                })
        
        if lines_to_create:
            self.env['sc360.indirect.cost.line'].create(lines_to_create)

    def action_draft(self):
        """Vuelve a borrador."""
        self.write({'state': 'draft'})
        self.distribution_line_ids.unlink()
        return True


class SC360IndirectCostLine(models.Model):
    """Línea de distribución de costo indirecto"""
    _name = 'sc360.indirect.cost.line'
    _description = 'Línea de Costo Indirecto'

    indirect_cost_id = fields.Many2one(
        'sc360.indirect.cost',
        'Costo indirecto',
        required=True,
        ondelete='cascade'
    )
    
    budget_line_id = fields.Many2one(
        'sc360.budget.line',
        'Concepto',
        required=True
    )
    
    amount = fields.Monetary(
        'Monto',
        required=True,
        currency_field='currency_id'
    )
    
    percentage = fields.Float(
        '% del concepto',
        compute='_compute_percentage',
        store=True,
        digits=(5, 2)
    )
    
    currency_id = fields.Many2one(
        related='indirect_cost_id.currency_id',
        store=True
    )

    @api.depends('amount', 'budget_line_id.amount_budget')
    def _compute_percentage(self):
        for line in self:
            if line.budget_line_id and line.budget_line_id.amount_budget:
                line.percentage = (line.amount / line.budget_line_id.amount_budget) * 100
            else:
                line.percentage = 0