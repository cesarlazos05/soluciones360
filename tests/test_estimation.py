# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestEstimation(TransactionCase):
    """Tests para la logica acumulada de estimaciones de avance de obra.

    Este es el test mas critico: verifica que cada estimacion toma
    correctamente el acumulado de la estimacion anterior y computa
    accum_total = accum_prev + this_estim, y remaining = contract_qty - accum_total.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._ensure_sequences()

        # Socio / contratista
        cls.partner = cls.env['res.partner'].create({
            'name': 'Subcontratista Estimaciones Test',
            'supplier_rank': 1,
        })

        # Proyecto de construccion
        cls.project = cls.env['project.project'].create({
            'name': 'Proyecto Test Estimaciones',
            'is_construction': True,
        })

        # Partida
        cls.category = cls.env['sc360.concept.category'].create({
            'name': 'Estructura Test',
            'code': 'ESTR-TEST',
        })

        # UdM
        cls.uom = cls.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if not cls.uom:
            cls.uom = cls.env['uom.uom'].search([], limit=1)

        # Conceptos del catalogo
        cls.concept1 = cls.env['sc360.concept.template'].create({
            'name': 'Cimentacion corrida',
            'category_id': cls.category.id,
            'uom_id': cls.uom.id,
            'default_price': 800.0,
        })
        cls.concept2 = cls.env['sc360.concept.template'].create({
            'name': 'Columnas de concreto',
            'category_id': cls.category.id,
            'uom_id': cls.uom.id,
            'default_price': 1200.0,
        })

        # Contrato con 2 lineas
        cls.contract = cls.env['sc360.contract'].create({
            'project_id': cls.project.id,
            'category_id': cls.category.id,
            'contractor_id': cls.partner.id,
        })
        cls.cl1 = cls.env['sc360.contract.line'].create({
            'contract_id': cls.contract.id,
            'concept_id': cls.concept1.id,
            'uom_id': cls.uom.id,
            'quantity': 200.0,  # Cantidad total contratada
            'unit_price': 800.0,
        })
        cls.cl2 = cls.env['sc360.contract.line'].create({
            'contract_id': cls.contract.id,
            'concept_id': cls.concept2.id,
            'uom_id': cls.uom.id,
            'quantity': 50.0,   # Cantidad total contratada
            'unit_price': 1200.0,
        })

    @classmethod
    def _ensure_sequences(cls):
        Sequence = cls.env['ir.sequence']
        for code, prefix in [
            ('sc360.contract', 'CON-'),
            ('sc360.estimate', 'EST-'),
            ('sc360.requisition', 'REQ-'),
        ]:
            if not Sequence.search([('code', '=', code)], limit=1):
                Sequence.create({
                    'name': code,
                    'code': code,
                    'prefix': prefix,
                    'padding': 5,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': False,
                })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_estimation_name_from_sequence(self):
        """El folio de estimacion debe asignarse desde la secuencia."""
        est = self.env['sc360.estimate'].create({
            'contract_id': self.contract.id,
            'period_start': '2025-01-01',
            'period_end': '2025-01-07',
        })
        self.assertNotEqual(est.name, 'Nuevo')
        self.assertTrue(est.name)

    def test_02_auto_number_within_contract(self):
        """Las estimaciones deben numerarse correlativamente por contrato."""
        contract2 = self.env['sc360.contract'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        })
        est_a = self.env['sc360.estimate'].create({
            'contract_id': contract2.id,
            'period_start': '2025-02-01',
            'period_end': '2025-02-07',
        })
        est_b = self.env['sc360.estimate'].create({
            'contract_id': contract2.id,
            'period_start': '2025-02-08',
            'period_end': '2025-02-14',
        })
        self.assertEqual(est_a.number, 1)
        self.assertEqual(est_b.number, 2)

    def test_03_accum_total_equals_prev_plus_this(self):
        """accum_total debe ser accum_prev + this_estim."""
        est = self.env['sc360.estimate'].create({
            'contract_id': self.contract.id,
            'period_start': '2025-03-01',
            'period_end': '2025-03-07',
        })
        line = self.env['sc360.estimate.line'].create({
            'estimate_id': est.id,
            'contract_line_id': self.cl1.id,
            'accum_prev': 30.0,
            'this_estim': 20.0,
        })
        self.assertAlmostEqual(line.accum_total, 50.0, places=4)

    def test_04_remaining_equals_contract_qty_minus_accum_total(self):
        """remaining debe ser contract_qty - accum_total."""
        est = self.env['sc360.estimate'].create({
            'contract_id': self.contract.id,
            'period_start': '2025-03-08',
            'period_end': '2025-03-14',
        })
        # cl1 tiene quantity=200
        line = self.env['sc360.estimate.line'].create({
            'estimate_id': est.id,
            'contract_line_id': self.cl1.id,
            'accum_prev': 50.0,
            'this_estim': 30.0,
        })
        # accum_total = 80; remaining = 200 - 80 = 120
        self.assertAlmostEqual(line.accum_total, 80.0, places=4)
        self.assertAlmostEqual(line.remaining, 120.0, places=4)

    def test_05_estimation1_approve_and_estimation2_accum_prev(self):
        """Flujo critico:
        - Estimacion #1: this_estim cargados, aprobar.
        - Estimacion #2: action_populate_lines debe cargar accum_prev
          igual al accum_total de la estimacion #1.
        """
        # Contrato independiente para este test (evitar interferencia)
        contract = self.env['sc360.contract'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        })
        cl_a = self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept1.id,
            'uom_id': self.uom.id,
            'quantity': 200.0,
            'unit_price': 800.0,
        })
        cl_b = self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept2.id,
            'uom_id': self.uom.id,
            'quantity': 50.0,
            'unit_price': 1200.0,
        })

        # --- Estimacion #1 ---
        est1 = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-04-01',
            'period_end': '2025-04-07',
        })
        # Poblar lineas manualmente (sin prev)
        line1_a = self.env['sc360.estimate.line'].create({
            'estimate_id': est1.id,
            'contract_line_id': cl_a.id,
            'accum_prev': 0.0,
            'this_estim': 40.0,
        })
        line1_b = self.env['sc360.estimate.line'].create({
            'estimate_id': est1.id,
            'contract_line_id': cl_b.id,
            'accum_prev': 0.0,
            'this_estim': 10.0,
        })

        # Verificar accum_total de estimacion #1
        self.assertAlmostEqual(line1_a.accum_total, 40.0, places=4)
        self.assertAlmostEqual(line1_b.accum_total, 10.0, places=4)

        # Aprobar estimacion #1
        est1.action_approve()
        self.assertEqual(est1.state, 'approved')

        # --- Estimacion #2 ---
        est2 = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-04-08',
            'period_end': '2025-04-14',
        })

        # action_populate_lines debe traer accum_prev de est1
        est2.action_populate_lines()
        self.assertEqual(len(est2.line_ids), 2)

        # Encontrar las lineas por contract_line_id
        l2_a = est2.line_ids.filtered(lambda l: l.contract_line_id == cl_a)
        l2_b = est2.line_ids.filtered(lambda l: l.contract_line_id == cl_b)

        self.assertTrue(l2_a, 'Debe existir linea para cl_a en estimacion 2')
        self.assertTrue(l2_b, 'Debe existir linea para cl_b en estimacion 2')

        # accum_prev de est2 debe ser accum_total de est1
        self.assertAlmostEqual(l2_a.accum_prev, line1_a.accum_total, places=4)
        self.assertAlmostEqual(l2_b.accum_prev, line1_b.accum_total, places=4)

    def test_06_estimation2_accum_total_after_this_estim(self):
        """accum_total en est2 = accum_prev (de est1) + this_estim de est2."""
        contract = self.env['sc360.contract'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        })
        cl = self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept1.id,
            'uom_id': self.uom.id,
            'quantity': 200.0,
            'unit_price': 800.0,
        })

        # Estimacion 1: this_estim = 60
        est1 = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-05-01',
            'period_end': '2025-05-07',
        })
        self.env['sc360.estimate.line'].create({
            'estimate_id': est1.id,
            'contract_line_id': cl.id,
            'accum_prev': 0.0,
            'this_estim': 60.0,
        })
        est1.action_approve()

        # Estimacion 2: poblar + asignar this_estim = 25
        est2 = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-05-08',
            'period_end': '2025-05-14',
        })
        est2.action_populate_lines()
        line2 = est2.line_ids[0]

        # accum_prev debe ser 60 (lo que acumulo est1)
        self.assertAlmostEqual(line2.accum_prev, 60.0, places=4)

        # Asignar avance de esta estimacion
        line2.this_estim = 25.0

        # accum_total = 60 + 25 = 85
        self.assertAlmostEqual(line2.accum_total, 85.0, places=4)

        # remaining = 200 - 85 = 115
        self.assertAlmostEqual(line2.remaining, 115.0, places=4)

    def test_07_estimate_total_is_sum_of_line_amounts(self):
        """El total de la estimacion debe ser la suma de los importes de las lineas."""
        est = self.env['sc360.estimate'].create({
            'contract_id': self.contract.id,
            'period_start': '2025-06-01',
            'period_end': '2025-06-07',
        })
        # Linea 1: this_estim=10, unit_price=800 => importe=8000
        self.env['sc360.estimate.line'].create({
            'estimate_id': est.id,
            'contract_line_id': self.cl1.id,
            'accum_prev': 0.0,
            'this_estim': 10.0,
        })
        # Linea 2: this_estim=5, unit_price=1200 => importe=6000
        self.env['sc360.estimate.line'].create({
            'estimate_id': est.id,
            'contract_line_id': self.cl2.id,
            'accum_prev': 0.0,
            'this_estim': 5.0,
        })
        # subtotal = 14000, iva = 0, total = 14000
        self.assertAlmostEqual(est.subtotal, 14000.0, places=2)
        self.assertAlmostEqual(est.iva_amount, 0.0, places=2)
        self.assertAlmostEqual(est.total, 14000.0, places=2)

    def test_08_only_approved_estimations_count_in_contract_amount_estimated(self):
        """Solo estimaciones aprobadas/pagadas suman al amount_estimated del contrato."""
        contract = self.env['sc360.contract'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        })
        cl = self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept1.id,
            'uom_id': self.uom.id,
            'quantity': 100.0,
            'unit_price': 500.0,
        })

        # Estimacion en borrador
        est_draft = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-07-01',
            'period_end': '2025-07-07',
        })
        self.env['sc360.estimate.line'].create({
            'estimate_id': est_draft.id,
            'contract_line_id': cl.id,
            'accum_prev': 0.0,
            'this_estim': 20.0,
        })
        # En draft: amount_estimated debe ser 0
        self.assertAlmostEqual(contract.amount_estimated, 0.0, places=2)

        # Aprobar
        est_draft.action_approve()
        # 20 * 500 = 10000
        self.assertAlmostEqual(contract.amount_estimated, 10000.0, places=2)

        # Segunda estimacion: pagada
        est2 = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-07-08',
            'period_end': '2025-07-14',
        })
        self.env['sc360.estimate.line'].create({
            'estimate_id': est2.id,
            'contract_line_id': cl.id,
            'accum_prev': 20.0,
            'this_estim': 15.0,
        })
        est2.action_approve()
        est2.action_pay()
        # total = (20*500) + (15*500) = 10000 + 7500 = 17500
        self.assertAlmostEqual(contract.amount_estimated, 17500.0, places=2)

    def test_09_state_transitions_estimation(self):
        """Verificar transiciones de estado: draft -> approved -> paid -> draft."""
        est = self.env['sc360.estimate'].create({
            'contract_id': self.contract.id,
            'period_start': '2025-08-01',
            'period_end': '2025-08-07',
        })
        self.assertEqual(est.state, 'draft')

        est.action_approve()
        self.assertEqual(est.state, 'approved')

        est.action_pay()
        self.assertEqual(est.state, 'paid')

        est.action_draft()
        self.assertEqual(est.state, 'draft')

    def test_10_populate_lines_with_no_previous_approved_estimation(self):
        """action_populate_lines sin estimacion previa aprobada debe poner accum_prev=0."""
        contract = self.env['sc360.contract'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        })
        self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept1.id,
            'uom_id': self.uom.id,
            'quantity': 100.0,
            'unit_price': 800.0,
        })
        self.env['sc360.contract.line'].create({
            'contract_id': contract.id,
            'concept_id': self.concept2.id,
            'uom_id': self.uom.id,
            'quantity': 30.0,
            'unit_price': 1200.0,
        })

        est = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-09-01',
            'period_end': '2025-09-07',
        })
        est.action_populate_lines()

        self.assertEqual(len(est.line_ids), 2)
        for line in est.line_ids:
            self.assertAlmostEqual(line.accum_prev, 0.0, places=4)
            self.assertAlmostEqual(line.this_estim, 0.0, places=4)
