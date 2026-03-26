# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestContract(TransactionCase):
    """Tests para el ciclo de vida del contrato de subcontratista."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear secuencias necesarias si no existen
        cls._ensure_sequences()

        # Socio / contratista
        cls.partner = cls.env['res.partner'].create({
            'name': 'Contratista Test SA',
            'supplier_rank': 1,
        })

        # Proyecto de construccion
        cls.project = cls.env['project.project'].create({
            'name': 'Proyecto Test Contrato',
            'is_construction': True,
        })

        # Partida / categoria de concepto
        cls.category = cls.env['sc360.concept.category'].create({
            'name': 'Albanileria Test',
            'code': 'ALB-TEST',
        })

        # Unidad de medida (usar la que ya exista en el sistema)
        cls.uom = cls.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if not cls.uom:
            cls.uom = cls.env['uom.uom'].search([], limit=1)

        # Plantilla de concepto
        cls.concept1 = cls.env['sc360.concept.template'].create({
            'name': 'Muro de tabique 10cm',
            'category_id': cls.category.id,
            'uom_id': cls.uom.id,
            'default_price': 350.0,
        })
        cls.concept2 = cls.env['sc360.concept.template'].create({
            'name': 'Aplanado de yeso',
            'category_id': cls.category.id,
            'uom_id': cls.uom.id,
            'default_price': 120.0,
        })

    @classmethod
    def _ensure_sequences(cls):
        """Asegurar que las secuencias requeridas existen."""
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

    def _create_contract(self, lines=None):
        """Helper: crea un contrato con las lineas indicadas."""
        vals = {
            'project_id': self.project.id,
            'category_id': self.category.id,
            'contractor_id': self.partner.id,
        }
        contract = self.env['sc360.contract'].create(vals)
        if lines:
            for line_vals in lines:
                line_vals['contract_id'] = contract.id
                self.env['sc360.contract.line'].create(line_vals)
        return contract

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_amount_total_computed_correctly(self):
        """amount_total debe ser la suma de quantity * unit_price de las lineas."""
        contract = self._create_contract(lines=[
            {
                'concept_id': self.concept1.id,
                'uom_id': self.uom.id,
                'quantity': 100.0,
                'unit_price': 350.0,
            },
            {
                'concept_id': self.concept2.id,
                'uom_id': self.uom.id,
                'quantity': 50.0,
                'unit_price': 120.0,
            },
        ])
        # 100 * 350 + 50 * 120 = 35000 + 6000 = 41000
        self.assertAlmostEqual(contract.amount_total, 41000.0, places=2)

    def test_02_state_draft_on_create(self):
        """Un contrato recien creado debe estar en estado 'draft'."""
        contract = self._create_contract()
        self.assertEqual(contract.state, 'draft')

    def test_03_action_activate_changes_state(self):
        """action_activate debe cambiar el estado a 'active'."""
        contract = self._create_contract()
        contract.action_activate()
        self.assertEqual(contract.state, 'active')

    def test_04_action_done_changes_state(self):
        """action_done debe cambiar el estado a 'done'."""
        contract = self._create_contract()
        contract.action_activate()
        contract.action_done()
        self.assertEqual(contract.state, 'done')

    def test_05_action_cancel_changes_state(self):
        """action_cancel debe cambiar el estado a 'cancel'."""
        contract = self._create_contract()
        contract.action_cancel()
        self.assertEqual(contract.state, 'cancel')

    def test_06_action_draft_resets_state(self):
        """action_draft debe regresar el estado a 'draft'."""
        contract = self._create_contract()
        contract.action_activate()
        contract.action_draft()
        self.assertEqual(contract.state, 'draft')

    def test_07_amount_estimated_only_approved(self):
        """amount_estimated solo debe sumar estimaciones en estado approved o paid."""
        contract = self._create_contract(lines=[
            {
                'concept_id': self.concept1.id,
                'uom_id': self.uom.id,
                'quantity': 100.0,
                'unit_price': 350.0,
            },
        ])
        cl = contract.line_ids[0]

        # Estimacion en borrador (no debe contar)
        est_draft = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-01-01',
            'period_end': '2025-01-07',
        })
        self.env['sc360.estimate.line'].create({
            'estimate_id': est_draft.id,
            'contract_line_id': cl.id,
            'accum_prev': 0.0,
            'this_estim': 20.0,
        })
        # En draft, amount_estimated debe ser 0
        self.assertAlmostEqual(contract.amount_estimated, 0.0, places=2)

        # Aprobar la estimacion
        est_draft.action_approve()
        # 20 * 350 = 7000
        self.assertAlmostEqual(contract.amount_estimated, 7000.0, places=2)

    def test_08_amount_remaining(self):
        """amount_remaining = amount_total - amount_estimated."""
        contract = self._create_contract(lines=[
            {
                'concept_id': self.concept1.id,
                'uom_id': self.uom.id,
                'quantity': 100.0,
                'unit_price': 350.0,
            },
        ])
        cl = contract.line_ids[0]

        # Sin estimaciones: remaining == total
        self.assertAlmostEqual(contract.amount_remaining, contract.amount_total, places=2)

        # Con estimacion aprobada
        est = self.env['sc360.estimate'].create({
            'contract_id': contract.id,
            'period_start': '2025-01-01',
            'period_end': '2025-01-07',
        })
        self.env['sc360.estimate.line'].create({
            'estimate_id': est.id,
            'contract_line_id': cl.id,
            'accum_prev': 0.0,
            'this_estim': 30.0,
        })
        est.action_approve()

        expected_estimated = 30.0 * 350.0  # 10500
        expected_remaining = contract.amount_total - expected_estimated
        self.assertAlmostEqual(contract.amount_remaining, expected_remaining, places=2)

    def test_09_name_assigned_from_sequence(self):
        """El folio del contrato debe asignarse desde la secuencia (no 'Nuevo')."""
        contract = self._create_contract()
        self.assertNotEqual(contract.name, 'Nuevo')
        self.assertTrue(contract.name)

    def test_10_estimation_count(self):
        """estimation_count debe reflejar el numero de estimaciones del contrato."""
        contract = self._create_contract()
        self.assertEqual(contract.estimation_count, 0)

        for i in range(3):
            self.env['sc360.estimate'].create({
                'contract_id': contract.id,
                'period_start': f'2025-0{i+1}-01',
                'period_end': f'2025-0{i+1}-07',
            })
        self.assertEqual(contract.estimation_count, 3)
