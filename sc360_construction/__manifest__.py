# -*- coding: utf-8 -*-
{
    'name': 'SC360 Construcción',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Gestión integral de proyectos de construcción para Soluciones Constructivas 360',
    'description': """
SC360 Construcción
==================

Módulo integral para gestión de proyectos de construcción:

* Catálogo maestro de conceptos y partidas
* Presupuestos por proyecto con control de ejecución
* Requisiciones de materiales (flujo directo sin aprobaciones)
* Generación de ODCs multi-proveedor desde requisiciones
* Trazabilidad completa: presupuesto vs comprado vs recibido
* Campos T.P.U. opcionales (informativos)

Desarrollado para Soluciones Constructivas 360.
    """,
    'author': 'Soluciones Constructivas 360',
    'website': 'https://sc360.mx',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'purchase',
        'stock',
        'product',
        'uom',
    ],
    'data': [
        # Seguridad
        'security/sc360_security.xml',
        'security/ir.model.access.csv',
        # Datos
        'data/sequence_data.xml',
        'data/uom_data.xml',
        # Vistas
        'views/concept_catalog_views.xml',
        'views/project_views.xml',
        'views/budget_line_views.xml',
        'views/requisition_views.xml',
        'views/purchase_views.xml',
        'views/menu.xml',
        # Wizards
        'wizard/generate_purchase_views.xml',
        'wizard/import_catalog_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'sc360_construction/static/src/css/sc360_styles.css',
        ],
    },
}
