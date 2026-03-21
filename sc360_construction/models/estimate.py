# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SC360Estimate(models.Model):
    """Estimación de Avance"""
    _name = 'sc360.estimate'
    _description = 'Estimación de Avance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_id desc, project_id, name'

    # Identificación
    name = fields.Char(
        'Folio',
        default='Nuevo',
        copy=False,
        readonly=True,
        index=True
    )
    
    # Relaciones principales
    project_id = fields.Many2one(
        'project.project',
        'Obra',
        required=True,
        tracking=True,
        domain=[('is_construction', '=', True)]
    )
    
    period_id = fields.Many2one(
        'sc360.estimate.period',
        'Período',
        required=True,
        tracking=True
    )
    
    contractor_id = fields.Many2one(
        'res.partner',
        'Contratista',
        domain=[('is_company', '=', True)],
        tracking=True,
        help="Empresa o persona que ejecuta los trabajos"
    )
    
    supervisor_id = fields.Many2one(
        'res.users',
        'Supervisor',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviada'),
        ('approved', 'Aprobada'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada'),
    ], default='draft', string='Estado', tracking=True, index=True)
    
    # Fechas
    date_submit = fields.Date('Fecha envío', readonly=True, copy=False)
    date_approve = fields.Date('Fecha aprobación', readonly=True, copy=False)
    date_pay = fields.Date('Fecha pago', readonly=True, copy=False)
    
    # Contrato
    contract_amount = fields.Monetary(
        'Monto contrato',
        related='project_id.total_budget',
        store=True,
        readonly=True,
        currency_field='currency_id',
        help="Monto total del contrato para referencia"
    )
    
    # Totales calculados
    amount_total = fields.Monetary(
        'Total estimado',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    amount_approved = fields.Monetary(
        'Total aprobado',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    amount_retention = fields.Monetary(
        'Retenciones',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    amount_to_pay = fields.Monetary(
        'A pagar',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    
    # Retención
    retention_pct = fields.Float(
        'Retención %',
        default=0.0,
        digits=(5, 2),
        help="Porcentaje de retención (anticipo, garantía, etc.)"
    )
    
    # Líneas de estimación
    line_ids = fields.One2many(
        'sc360.estimate.line',
        'estimate_id',
        string='Conceptos'
    )
    line_count = fields.Integer(
        compute='_compute_line_count',
        string='Número de conceptos'
    )
    
    # Evidencias
    evidence_ids = fields.Many2many(
        'ir.attachment',
        'sc360_estimate_attachment_rel',
        'estimate_id',
        'attachment_id',
        string='Evidencias fotográficas'
    )
    
    # Mano de obra
    labor_cost_ids = fields.One2many(
        'sc360.labor.cost',
        'estimate_id',
        string='Mano de obra'
    )
    labor_total = fields.Monetary(
        'Total mano de obra',
        compute='_compute_labor_total',
        store=True,
        currency_field='currency_id'
    )
    
    # Notas
    notes = fields.Text('Notas / Observaciones')
    rejection_reason = fields.Text('Motivo de rechazo')
    
    # Moneda
    currency_id = fields.Many2one(
        related='project_id.currency_id',
        store=True
    )
    company_id = fields.Many2one(
        related='project_id.company_id',
        store=True
    )
    
    # Acumulados del proyecto (para referencia)
    previous_amount = fields.Monetary(
        'Acumulado anterior',
        compute='_compute_previous',
        store=False,
        currency_field='currency_id',
        help="Total de estimaciones aprobadas anteriores"
    )
    accumulated_amount = fields.Monetary(
        'Acumulado total',
        compute='_compute_previous',
        store=False,
        currency_field='currency_id',
        help="Total acumulado incluyendo esta estimación"
    )
    progress_pct = fields.Float(
        '% Avance acumulado',
        compute='_compute_previous',
        store=False,
        digits=(5, 2),
        help="Porcentaje de avance del contrato"
    )

    # === Métodos de creación ===

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('sc360.estimate') or 'Nuevo'
        return super().create(vals_list)

    # === Métodos compute ===

    def _compute_line_count(self):
        for estimate in self:
            estimate.line_count = len(estimate.line_ids)

    @api.depends('line_ids.qty_this', 'line_ids.amount_approved', 'state')
    def _compute_totals(self):
        for estimate in self:
            estimate.amount_total = sum(estimate.line_ids.mapped('amount_this'))
            
            approved_lines = estimate.line_ids.filtered(lambda l: estimate.state in ['approved', 'paid'])
            estimate.amount_approved = sum(approved_lines.mapped('amount_approved'))
            
            # Retención
            estimate.amount_retention = estimate.amount_approved * (estimate.retention_pct / 100)
            estimate.amount_to_pay = estimate.amount_approved - estimate.amount_retention

    def _compute_labor_total(self):
        """Calcula el total de mano de obra."""
        for estimate in self:
            estimate.labor_total = sum(estimate.labor_cost_ids.mapped('amount'))

    def _compute_previous(self):
        """Calcula acumulados anteriores del proyecto."""
        for estimate in self:
            if not estimate.project_id or not estimate.period_id:
                estimate.previous_amount = 0
                estimate.accumulated_amount = 0
                estimate.progress_pct = 0
                continue
            
            # Buscar estimaciones aprobadas anteriores
            previous_estimates = self.search([
                ('project_id', '=', estimate.project_id.id),
                ('state', 'in', ['approved', 'paid']),
                ('period_id.date_end', '<', estimate.period_id.date_start),
            ])
            
            estimate.previous_amount = sum(prev.amount_approved for prev in previous_estimates)
            estimate.accumulated_amount = estimate.previous_amount + estimate.amount_total
            
            # Calcular % de avance
            if estimate.project_id.total_budget:
                estimate.progress_pct = (estimate.accumulated_amount / estimate.project_id.total_budget) * 100
            else:
                estimate.progress_pct = 0

    # === Métodos de línea ===

    def action_add_all_concepts(self):
        """Añade todas las líneas de presupuesto del proyecto."""
        self.ensure_one()
        if not self.project_id:
            raise UserError(_('Debe seleccionar una obra primero.'))
        
        budget_lines = self.env['sc360.budget.line'].search([
            ('project_id', '=', self.project_id.id),
            ('active', '=', True)
        ])
        
        if not budget_lines:
            raise UserError(_('No hay conceptos en el presupuesto de esta obra.'))
        
        # Obtener conceptos ya existentes
        existing_concepts = self.line_ids.mapped('budget_line_id')
        
        lines_to_create = []
        for budget_line in budget_lines:
            if budget_line not in existing_concepts:
                lines_to_create.append({
                    'estimate_id': self.id,
                    'budget_line_id': budget_line.id,
                })
        
        if lines_to_create:
            self.env['sc360.estimate.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conceptos añadidos'),
                'message': _('Se añadieron %d conceptos del presupuesto.') % len(lines_to_create),
                'type': 'success',
                'sticky': False,
            }
        }

    # === Métodos de flujo ===

    def action_submit(self):
        """Envía estimación para revisión."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('La estimación debe tener al menos una línea.'))
        
        # Validar que todas las líneas tengan cantidad
        for line in self.line_ids:
            if line.qty_this <= 0:
                raise UserError(_('Todas las cantidades deben ser mayores a cero.'))
        
        self.write({
            'state': 'submitted',
            'date_submit': fields.Date.today(),
        })
        
        # Notificar al supervisor
        if self.project_id.supervisor_id:
            self.message_post(
                body=_('Estimación enviada para revisión'),
                partner_ids=[self.project_id.supervisor_id.partner_id.id]
            )
        
        return True

    def action_approve(self):
        """Aprueba la estimación."""
        self.ensure_one()
        
        # Copiar cantidades aprobadas
        for line in self.line_ids:
            line.write({
                'qty_approved': line.qty_this,
                'amount_approved': line.amount_this,
            })
        
        self.write({
            'state': 'approved',
            'date_approve': fields.Date.today(),
        })
        
        # Actualizar acumulados en budget.line
        self._update_budget_accumulated()
        
        return True

    def action_reject(self):
        """Rechaza la estimación."""
        self.ensure_one()
        if not self.rejection_reason:
            raise UserError(_('Debe indicar el motivo de rechazo.'))
        
        self.write({'state': 'draft'})
        
        self.message_post(
            body=_('Estimación rechazada: %s') % self.rejection_reason
        )
        
        return True

    def action_pay(self):
        """Marca como pagada."""
        self.ensure_one()
        self.write({
            'state': 'paid',
            'date_pay': fields.Date.today(),
        })
        return True

    def action_cancel(self):
        """Cancela la estimación."""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        """Vuelve a borrador."""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    def _update_budget_accumulated(self):
        """Actualiza los acumulados en las líneas de presupuesto."""
        for line in self.line_ids:
            # Buscar estimaciones aprobadas anteriores
            previous_lines = self.env['sc360.estimate.line'].search([
                ('budget_line_id', '=', line.budget_line_id.id),
                ('estimate_id.project_id', '=', self.project_id.id),
                ('estimate_id.state', 'in', ['approved', 'paid']),
                ('estimate_id.period_id.date_end', '<', self.period_id.date_start),
            ])
            
            previous_amount = sum(previous_lines.mapped('amount_approved'))
            
            line.budget_line_id.write({
                'amount_estimated': previous_amount + line.amount_approved,
                'qty_estimated': line.qty_approved,
            })

    # === Vistas ===

    def action_view_lines(self):
        """Ver líneas de estimación."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conceptos'),
            'res_model': 'sc360.estimate.line',
            'view_mode': 'list,form',
            'domain': [('estimate_id', '=', self.id)],
            'context': {'default_estimate_id': self.id},
        }

    # === Onchanges ===

    @api.onchange('project_id')
    def _onchange_project(self):
        """Carga datos del proyecto."""
        if self.project_id:
            self.contract_amount = self.project_id.total_budget
            self.supervisor_id = self.project_id.supervisor_id


class SC360EstimateLine(models.Model):
    """Línea de Estimación"""
    _name = 'sc360.estimate.line'
    _description = 'Línea de Estimación'
    _order = 'estimate_id, sequence'

    # Relaciones
    estimate_id = fields.Many2one(
        'sc360.estimate',
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
    
    sequence = fields.Integer('No.', default=10)
    
    # Datos del concepto (related)
    code = fields.Char(
        related='budget_line_id.code',
        string='Código',
        readonly=True,
        store=True
    )
    name = fields.Char(
        related='budget_line_id.name',
        string='Concepto',
        readonly=True,
        store=True
    )
    category_id = fields.Many2one(
        related='budget_line_id.category_id',
        string='Partida',
        readonly=True,
        store=True
    )
    uom_id = fields.Many2one(
        related='budget_line_id.uom_id',
        string='Unidad',
        readonly=True,
        store=True
    )
    
    # Presupuesto (related)
    qty_budget = fields.Float(
        related='budget_line_id.qty_budget',
        string='Cant. Presup.',
        readonly=True,
        store=True
    )
    unit_price = fields.Monetary(
        related='budget_line_id.unit_price',
        string='P.U.',
        readonly=True,
        store=True,
        currency_field='currency_id'
    )
    amount_budget = fields.Monetary(
        related='budget_line_id.amount_budget',
        string='Importe Presup.',
        readonly=True,
        store=True,
        currency_field='currency_id'
    )
    
    # Acumulado anterior (calculado)
    qty_previous = fields.Float(
        'Cant. Anterior',
        compute='_compute_previous',
        store=True,
        digits='Product Unit of Measure'
    )
    amount_previous = fields.Monetary(
        'Importe Anterior',
        compute='_compute_previous',
        store=True,
        currency_field='currency_id'
    )
    
    # Esta estimación
    qty_this = fields.Float(
        'Cantidad esta est.',
        required=True,
        digits='Product Unit of Measure',
        default=0.0
    )
    unit_price_this = fields.Monetary(
        'P.U. esta est.',
        currency_field='currency_id',
        help="Precio unitario para esta estimación. Si vacío, usa el del presupuesto."
    )
    amount_this = fields.Monetary(
        'Importe esta est.',
        compute='_compute_amount_this',
        store=True,
        currency_field='currency_id'
    )
    
    # Acumulado total
    qty_accumulated = fields.Float(
        'Cant. Acumulada',
        compute='_compute_accumulated',
        store=True,
        digits='Product Unit of Measure'
    )
    amount_accumulated = fields.Monetary(
        'Importe Acumulado',
        compute='_compute_accumulated',
        store=True,
        currency_field='currency_id'
    )
    
    # Avance (%)
    progress_qty = fields.Float(
        '% Avance cant.',
        compute='_compute_progress',
        store=True,
        digits=(5, 2)
    )
    progress_amount = fields.Float(
        '% Avance importe',
        compute='_compute_progress',
        store=True,
        digits=(5, 2)
    )
    
    # Aprobación
    qty_approved = fields.Float(
        'Cant. Aprobada',
        digits='Product Unit of Measure',
        default=0.0
    )
    amount_approved = fields.Monetary(
        'Importe Aprobado',
        currency_field='currency_id'
    )
    
    # Variación
    variance_amount = fields.Monetary(
        'Variación $',
        compute='_compute_variance',
        store=True,
        currency_field='currency_id'
    )
    variance_pct = fields.Float(
        'Variación %',
        compute='_compute_variance',
        store=True,
        digits=(5, 2)
    )
    
    # Notas
    notes = fields.Text('Observaciones')
    
    # Moneda
    currency_id = fields.Many2one(
        related='estimate_id.currency_id',
        store=True
    )

    # === Constraints ===

    @api.constrains('qty_this')
    def _check_qty_this(self):
        for line in self:
            if line.qty_this < 0:
                raise ValidationError(_('La cantidad no puede ser negativa.'))

    # === Computes ===

    @api.depends('qty_this', 'unit_price_this', 'unit_price')
    def _compute_amount_this(self):
        for line in self:
            price = line.unit_price_this or line.unit_price
            line.amount_this = line.qty_this * price

    @api.depends('estimate_id', 'budget_line_id')
    def _compute_previous(self):
        """Calcula acumulado anterior desde estimaciones aprobadas."""
        for line in self:
            if not line.estimate_id or not line.budget_line_id:
                line.qty_previous = 0
                line.amount_previous = 0
                continue
            
            # Buscar líneas de estimaciones aprobadas anteriores
            previous_lines = self.search([
                ('budget_line_id', '=', line.budget_line_id.id),
                ('estimate_id.project_id', '=', line.estimate_id.project_id.id),
                ('estimate_id.state', 'in', ['approved', 'paid']),
                ('estimate_id.period_id.date_end', '<', line.estimate_id.period_id.date_start),
            ])
            
            line.qty_previous = sum(previous_lines.mapped('qty_approved'))
            line.amount_previous = sum(previous_lines.mapped('amount_approved'))

    @api.depends('qty_this', 'qty_previous', 'amount_this', 'amount_previous')
    def _compute_accumulated(self):
        for line in self:
            line.qty_accumulated = line.qty_previous + line.qty_this
            line.amount_accumulated = line.amount_previous + line.amount_this

    @api.depends('qty_accumulated', 'amount_accumulated', 'qty_budget', 'amount_budget')
    def _compute_progress(self):
        for line in self:
            if line.qty_budget:
                line.progress_qty = (line.qty_accumulated / line.qty_budget) * 100
            else:
                line.progress_qty = 0
            
            if line.amount_budget:
                line.progress_amount = (line.amount_accumulated / line.amount_budget) * 100
            else:
                line.progress_amount = 0

    @api.depends('amount_approved', 'amount_this')
    def _compute_variance(self):
        for line in self:
            # Variación entre aprobado y estimado
            line.variance_amount = line.amount_approved - line.amount_this
            if line.amount_this:
                line.variance_pct = (line.variance_amount / line.amount_this) * 100
            else:
                line.variance_pct = 0

    # === Onchanges ===

    @api.onchange('budget_line_id')
    def _onchange_budget_line(self):
        """Carga datos del presupuesto."""
        if self.budget_line_id:
            self.unit_price_this = self.budget_line_id.unit_price

    # === Actions ===

    def action_approve_line(self):
        """Aprueba esta línea individualmente."""
        self.ensure_one()
        self.write({
            'qty_approved': self.qty_this,
            'amount_approved': self.amount_this,
        })
        return True