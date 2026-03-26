{
    'name': 'SC360 Construccion',
    'version': '19.0.5.1.0',
    'category': 'Construction',
    'summary': 'Gestion de proyectos de construccion con presupuestos, '
               'requisiciones, contratos y estimaciones',
    'description': 'Modulo para Soluciones Constructivas 360',
    'author': 'Orvin Odoo',
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
        'security/sc360_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
    ],
    'application': True,
    'installable': True,
}
