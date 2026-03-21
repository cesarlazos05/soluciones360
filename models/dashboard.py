# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SC360Dashboard(models.Model):
    """Dashboard ejecutivo - Modelo computado (sin SQL view)"""
    _name = 'sc360.dashboard'
    _description = 'Dashboard Ejecutivo SC360'
    _auto = False

    # Este modelo no tiene tabla, se usa como placeholder
    # Los KPIs se calculan dinámicamente desde project.project

    # Campos dummy para que el modelo sea válido
    id = fields.Integer('ID', readonly=True)
    name = fields.Char('Nombre', readonly=True)
    value = fields.Float('Valor', readonly=True)

    def init(self):
        """No crea vista SQL, el modelo se maneja en memoria."""
        # Eliminar vista si existe
        self.env.cr.execute("""
            DROP VIEW IF EXISTS sc360_dashboard;
        """)