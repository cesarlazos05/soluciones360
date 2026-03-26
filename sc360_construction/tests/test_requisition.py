# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestRequisition(TransactionCase):
    """Tests para el flujo de aprobacion de requisiciones de materiales."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Secuencias
        cls._ensure_sequences()

        # Proyecto de construccion
        cls.project = cls.env['project.project'].create({
            'name': 'Proyecto Test Requisicion',
            'is_construction': True,
        })

        # Partida
        cls.category = cls.env['sc360.concept.category'].create({
            'name': 'Electrico Test',
            'code': 'ELEC-TEST',
        })

        # Concepto
        cls.uom = cls.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if not cls.uom:
            cls.uom = cls.env['uom.uom'].search([], limit=1)

        # Producto comprable para las lineas de requisicion
        cls.product = cls.env['product.product'].create({
            'name': 'Cable THW 12 AWG',
            'purchase_ok': True,
            'type': 'consu',
            'uom_id': cls.uom.id,
            'uom_po_id': cls.uom.id,
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

    def _create_requisition(self, with_lines=True):
        """Helper: crea una requisicion, opcionalmente con una linea."""
        req = self.env['sc360.requisition'].create({
            'project_id': self.project.id,
            'category_id': self.category.id,
        })
        if with_lines:
            self.env['sc360.requisition.line'].create({
                'requisition_id': req.id,
                'product_id': self.product.id,
                'quantity': 100.0,
                'uom_id': self.uom.id,
            })
        return req

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_state_draft_on_create(self):
        """Una requisicion recien creada debe estar en estado 'draft'."""
        req = self._create_requisition()
        self.assertEqual(req.state, 'draft')

    def test_02_name_assigned_from_sequence(self):
        """El folio debe asignarse desde la secuencia (no 'Nuevo')."""
        req = self._create_requisition()
        self.assertNotEqual(req.name, 'Nuevo')
        self.assertTrue(req.name)

    def test_03_action_send_requires_lines(self):
        """action_send debe lanzar UserError si no hay lineas."""
        req = self._create_requisition(with_lines=False)
        with self.assertRaises(UserError):
            req.action_send()

    def test_04_action_send_changes_state_to_sent(self):
        """action_send con lineas debe cambiar estado a 'sent'."""
        req = self._create_requisition(with_lines=True)
        req.action_send()
        self.assertEqual(req.state, 'sent')

    def test_05_action_approve_changes_state(self):
        """action_approve debe cambiar el estado a 'approved'."""
        req = self._create_requisition()
        req.action_send()
        req.action_approve()
        self.assertEqual(req.state, 'approved')

    def test_06_action_reject_resets_to_draft(self):
        """action_reject debe regresar el estado a 'draft'."""
        req = self._create_requisition()
        req.action_send()
        req.action_reject()
        self.assertEqual(req.state, 'draft')

    def test_07_action_done_changes_state(self):
        """action_done debe cambiar el estado a 'done'."""
        req = self._create_requisition()
        req.action_send()
        req.action_approve()
        req.action_done()
        self.assertEqual(req.state, 'done')

    def test_08_full_workflow(self):
        """Flujo completo: draft -> sent -> approved -> done."""
        req = self._create_requisition()
        self.assertEqual(req.state, 'draft')

        req.action_send()
        self.assertEqual(req.state, 'sent')

        req.action_approve()
        self.assertEqual(req.state, 'approved')

        req.action_done()
        self.assertEqual(req.state, 'done')

    def test_09_reject_after_send_returns_to_draft(self):
        """Se puede rechazar una requisicion enviada y vuelve a borrador."""
        req = self._create_requisition()
        req.action_send()
        self.assertEqual(req.state, 'sent')

        req.action_reject()
        self.assertEqual(req.state, 'draft')

        # Debe poder enviarse de nuevo
        req.action_send()
        self.assertEqual(req.state, 'sent')

    def test_10_purchase_count_zero_on_create(self):
        """Una requisicion nueva no debe tener ordenes de compra."""
        req = self._create_requisition()
        self.assertEqual(req.purchase_count, 0)

    def test_11_requester_defaults_to_current_user(self):
        """El solicitante debe ser el usuario actual por defecto."""
        req = self._create_requisition()
        self.assertEqual(req.requester_id, self.env.user)
