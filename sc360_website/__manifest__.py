{
    'name': 'SC360 Website Landing Page',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Landing page para SC360 Constructora',
    'description': """
        Landing page corporativa para SC360 — Soluciones Constructivas 360.
        Incluye hero, servicios, proceso, proyectos, testimonial y CTA.
    """,
    'author': 'SC360',
    'website': 'https://sc360.mx',
    'depends': ['website'],
    'data': [
        'views/sc360_landing_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sc360_website/static/src/css/sc360_fonts.css',
            'sc360_website/static/src/css/sc360_landing.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
