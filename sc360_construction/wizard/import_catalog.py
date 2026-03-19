import base64
import io
from odoo import models, fields, api
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None


class ImportCatalogWizard(models.TransientModel):
    """Wizard para importar catálogo de conceptos desde Excel"""
    _name = 'sc360.import.catalog.wizard'
    _description = 'Importar catálogo desde Excel'

    file = fields.Binary("Archivo Excel", required=True)
    filename = fields.Char("Nombre archivo")
    
    import_type = fields.Selection([
        ('catalog', 'Catálogo maestro'),
        ('budget', 'Presupuesto de proyecto'),
    ], string="Tipo de importación", default='catalog', required=True)
    
    project_id = fields.Many2one(
        'project.project',
        string="Proyecto destino",
        help="Solo para importación de presupuesto"
    )
    
    # Opciones
    update_existing = fields.Boolean(
        "Actualizar existentes",
        default=False,
        help="Si encuentra registros con el mismo código, los actualiza en lugar de omitirlos"
    )
    create_products = fields.Boolean(
        "Crear productos automáticamente",
        default=False,
        help="Crea productos en Odoo para los materiales que no existan"
    )
    
    # Resultados
    result_message = fields.Text("Resultado", readonly=True)
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('done', 'Completado'),
    ], default='draft')

    @api.onchange('import_type')
    def _onchange_import_type(self):
        if self.import_type == 'catalog':
            self.project_id = False

    def action_import(self):
        """Ejecuta la importación"""
        self.ensure_one()
        
        if not openpyxl:
            raise UserError(
                "La librería 'openpyxl' no está instalada.\n"
                "Contacte al administrador para instalarla: pip install openpyxl"
            )
        
        if self.import_type == 'budget' and not self.project_id:
            raise UserError("Debe seleccionar un proyecto para importar el presupuesto.")
        
        # Leer archivo
        try:
            file_content = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {str(e)}")
        
        if self.import_type == 'catalog':
            result = self._import_catalog(workbook)
        else:
            result = self._import_budget(workbook)
        
        self.write({
            'result_message': result,
            'state': 'done',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _import_catalog(self, workbook):
        """Importa partidas y conceptos al catálogo maestro"""
        sheet = workbook.active
        
        created_categories = 0
        created_concepts = 0
        updated = 0
        errors = []
        
        Category = self.env['sc360.concept.category']
        Concept = self.env['sc360.concept.template']
        Uom = self.env['uom.uom']
        
        current_category = None
        
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                if not any(row):
                    continue
                
                # Detectar si es partida o concepto por la estructura
                # Asumimos: Col A = Código partida, Col B = Nombre partida, 
                #           Col C = Código concepto, Col D = Nombre concepto,
                #           Col E = Descripción, Col F = Unidad, Col G = P.U.
                
                partida_code = str(row[0]).strip() if row[0] else None
                partida_name = str(row[1]).strip() if row[1] else None
                concepto_code = str(row[2]).strip() if row[2] else None
                concepto_name = str(row[3]).strip() if row[3] else None
                descripcion = str(row[4]).strip() if row[4] else None
                unidad = str(row[5]).strip() if row[5] else None
                precio = float(row[6]) if row[6] else 0.0
                
                # Si tiene código de partida y nombre, crear/buscar partida
                if partida_code and partida_name:
                    existing = Category.search([('code', '=', partida_code)], limit=1)
                    if existing:
                        if self.update_existing:
                            existing.write({'name': partida_name})
                            updated += 1
                        current_category = existing
                    else:
                        current_category = Category.create({
                            'code': partida_code,
                            'name': partida_name,
                        })
                        created_categories += 1
                
                # Si tiene concepto, crearlo
                if concepto_name and current_category:
                    # Buscar unidad de medida
                    uom = Uom.search([
                        '|', ('name', 'ilike', unidad), ('display_name', 'ilike', unidad)
                    ], limit=1) if unidad else Uom.search([('name', '=', 'Unidades')], limit=1)
                    
                    if not uom:
                        uom = Uom.search([], limit=1)
                    
                    existing_concept = Concept.search([
                        ('code', '=', concepto_code),
                        ('category_id', '=', current_category.id)
                    ], limit=1) if concepto_code else False
                    
                    if existing_concept:
                        if self.update_existing:
                            existing_concept.write({
                                'name': concepto_name,
                                'description': descripcion,
                                'uom_id': uom.id,
                                'base_unit_price': precio,
                            })
                            updated += 1
                    else:
                        Concept.create({
                            'code': concepto_code,
                            'name': concepto_name,
                            'description': descripcion,
                            'category_id': current_category.id,
                            'uom_id': uom.id,
                            'base_unit_price': precio,
                        })
                        created_concepts += 1
                        
            except Exception as e:
                errors.append(f"Fila {row_num}: {str(e)}")
        
        result = f"""
IMPORTACIÓN DE CATÁLOGO COMPLETADA
==================================
Partidas creadas: {created_categories}
Conceptos creados: {created_concepts}
Registros actualizados: {updated}
"""
        if errors:
            result += f"\nErrores ({len(errors)}):\n" + "\n".join(errors[:20])
            if len(errors) > 20:
                result += f"\n... y {len(errors) - 20} errores más"
        
        return result

    def _import_budget(self, workbook):
        """Importa presupuesto a un proyecto específico"""
        sheet = workbook.active
        
        created_lines = 0
        errors = []
        
        BudgetLine = self.env['sc360.budget.line']
        Category = self.env['sc360.concept.category']
        Uom = self.env['uom.uom']
        
        current_category = None
        
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                if not any(row):
                    continue
                
                # Estructura esperada del presupuesto:
                # Col A = No., Col B = Clave, Col C = Concepto, Col D = Unidad,
                # Col E = Cantidad, Col F = P.U., Col G = Importe
                
                numero = row[0]
                clave = str(row[1]).strip() if row[1] else None
                concepto = str(row[2]).strip() if row[2] else None
                unidad = str(row[3]).strip() if row[3] else None
                cantidad = float(row[4]) if row[4] else 0.0
                precio = float(row[5]) if row[5] else 0.0
                
                if not concepto:
                    continue
                
                # Detectar si es una partida (generalmente no tiene cantidad ni precio)
                is_partida = not cantidad and not precio and concepto
                
                if is_partida:
                    # Buscar o crear partida
                    existing_cat = Category.search([
                        '|', ('code', '=', clave), ('name', '=', concepto)
                    ], limit=1)
                    
                    if existing_cat:
                        current_category = existing_cat
                    else:
                        current_category = Category.create({
                            'code': clave or f'P{row_num}',
                            'name': concepto,
                        })
                    continue
                
                # Es una línea de concepto
                if not current_category:
                    # Crear categoría genérica
                    current_category = Category.search([('code', '=', 'GEN')], limit=1)
                    if not current_category:
                        current_category = Category.create({
                            'code': 'GEN',
                            'name': 'General',
                        })
                
                # Buscar unidad de medida
                uom = Uom.search([
                    '|', ('name', 'ilike', unidad), ('display_name', 'ilike', unidad)
                ], limit=1) if unidad else None
                
                if not uom:
                    uom = Uom.search([('name', '=', 'Unidades')], limit=1) or Uom.search([], limit=1)
                
                BudgetLine.create({
                    'project_id': self.project_id.id,
                    'sequence': int(numero) if numero else row_num,
                    'category_id': current_category.id,
                    'code': clave,
                    'name': concepto,
                    'uom_id': uom.id,
                    'qty_budget': cantidad,
                    'unit_price': precio,
                })
                created_lines += 1
                
            except Exception as e:
                errors.append(f"Fila {row_num}: {str(e)}")
        
        result = f"""
IMPORTACIÓN DE PRESUPUESTO COMPLETADA
=====================================
Proyecto: {self.project_id.name}
Líneas creadas: {created_lines}
"""
        if errors:
            result += f"\nErrores ({len(errors)}):\n" + "\n".join(errors[:20])
            if len(errors) > 20:
                result += f"\n... y {len(errors) - 20} errores más"
        
        return result

    def action_download_template(self):
        """Descarga plantilla de ejemplo"""
        # En producción, esto generaría un archivo de plantilla
        raise UserError(
            "Para importar correctamente, su archivo Excel debe tener la siguiente estructura:\n\n"
            "CATÁLOGO MAESTRO:\n"
            "Columna A: Código partida\n"
            "Columna B: Nombre partida\n"
            "Columna C: Código concepto\n"
            "Columna D: Nombre concepto\n"
            "Columna E: Descripción\n"
            "Columna F: Unidad\n"
            "Columna G: P.U.\n\n"
            "PRESUPUESTO:\n"
            "Columna A: No.\n"
            "Columna B: Clave\n"
            "Columna C: Concepto\n"
            "Columna D: Unidad\n"
            "Columna E: Cantidad\n"
            "Columna F: P.U.\n"
            "Columna G: Importe"
        )
