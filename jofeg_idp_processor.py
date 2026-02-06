
import os
import re
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
import fitz  # PyMuPDF

# ==============================================================================
# CONFIGURACIÓN (Ajustar según entorno Jofeg)
# ==============================================================================
INPUT_PDF_DIR = r"X:\Facts_Proveedor"  # <--- Cambiar a la ruta real de SharePoint
PROVEE_CSV_PATH = r"X:\DatosCsv\PROVEE.csv"
OUTPUT_XLSX = r"c:\Proyectos\Proveedores\Resumen_Facturas_IDP.xlsx"
STATE_PATH = r"c:\Proyectos\Proveedores\processing_state.json"
LOG_FILE = r"c:\Proyectos\Proveedores\idp_processor.log"
TEMPLATES_PATH = r"c:\Proyectos\Proveedores\templates.json"

# Expresiones Regulares alineadas con estándares de Facturación e IDP
REGEX_CIF = r'[ABCDEFGHJNPQRSUVW][0-9]{7}[A-Z0-9]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE]'
REGEX_DATE = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
REGEX_AMOUNT = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2,}))'
REGEX_IVA_LABEL = r'(?i)(?:IVA|CUOTA|I\.V\.A\.|IMPUESTO)[\s:º=]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2,}))'
REGEX_BASE_LABEL = r'(?i)(?:BASE|B\.I\.|BI|NETO|SUBTOTAL)[\s:º=]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2,}))'

# CIF de JOFEG (cliente) - EXCLUIR de la detección de proveedor
JOFEG_CIF = "A28346245"

# ==============================================================================
# LOGGING (Trazabilidad e-EMGDE)
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class JofegIDPProcessor:
    def __init__(self, use_claude_api=True, claude_as_fallback_only=True):
        """
        Args:
            use_claude_api: Si True, usa Claude API cuando sea necesario
            claude_as_fallback_only: Si True, solo usa Claude API cuando no hay plantilla
        """
        self.state = self._load_state()
        self.suppliers = self._load_suppliers()
        self.templates = self._load_templates()
        self._ensure_output_dir()
        
        # Configuración de Claude API
        self.use_claude_api = use_claude_api
        self.claude_as_fallback_only = claude_as_fallback_only
        self.claude_extractor = None
        
        if self.use_claude_api:
            try:
                from claude_extractor import ClaudeIDPExtractor
                self.claude_extractor = ClaudeIDPExtractor()
                logging.info("Claude API configurada correctamente")
            except Exception as e:
                logging.warning(f"Claude API no disponible: {e}")

    def _load_templates(self):
        if os.path.exists(TEMPLATES_PATH):
            try:
                with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logging.info(f"[TEMPLATES]: Cargadas {len(data)} plantillas desde {TEMPLATES_PATH}")
                    logging.info(f"[TEMPLATES]: Claves encontradas: {list(data.keys())}")
                    return data
            except Exception as e:
                logging.error(f"Error cargando plantillas: {e}")
                return {}
        logging.warning(f"No se encontró archivo de plantillas en {TEMPLATES_PATH}")
        return {}

    def _ensure_output_dir(self):
        os.makedirs(os.path.dirname(OUTPUT_XLSX), exist_ok=True)

    def _load_state(self):
        if os.path.exists(STATE_PATH):
            try:
                with open(STATE_PATH, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self):
        with open(STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=4)

    def _load_suppliers(self):
        """Carga y normaliza el maestro de proveedores (PROVEE.csv)"""
        try:
            if not os.path.exists(PROVEE_CSV_PATH):
                logging.warning(f"No se encontró el archivo maestro en {PROVEE_CSV_PATH}")
                return pd.DataFrame(columns=['CUENTA', 'NOMBRE', 'CIF', 'CIF_NORM'])
            
            # Carga de columnas específicas: 0:CUENTA, 1:NOMBRE, 9:CIF
            df = pd.read_csv(PROVEE_CSV_PATH, header=None, encoding='latin1', dtype=str)
            df = df[[0, 1, 9]]
            df.columns = ['CUENTA', 'NOMBRE', 'CIF']
            df['CIF_NORM'] = df['CIF'].apply(self.normalize_id)
            logging.info(f"Maestro cargado: {len(df)} proveedores.")
            return df
        except Exception as e:
            logging.error(f"Error cargando maestro de proveedores: {e}")
            return pd.DataFrame(columns=['CUENTA', 'NOMBRE', 'CIF', 'CIF_NORM'])

    @staticmethod
    def normalize_id(text):
        """Limpia CIF/NIF de caracteres especiales para matching exacto"""
        if not text or pd.isna(text): return ""
        norm = re.sub(r'[^A-Z0-9]', '', str(text).upper())
        # Eliminar prefijo ES si está presente (común en facturas pero no en ERP)
        if norm.startswith("ES") and len(norm) > 7:
            return norm[2:]
        return norm

    def get_file_fingerprint(self, filepath):
        """Genera una huella digital única (mtime + size) para procesamiento incremental"""
        stats = os.stat(filepath)
        return f"{stats.st_mtime}-{stats.st_size}"

    def extract_idp_data(self, pdf_path):
        """Extrae texto, metadatos y valida cumplimiento PDF/A"""
        text = ""
        metadata = {}
        try:
            doc = fitz.open(pdf_path)
            metadata['pages'] = len(doc)
            metadata['format'] = doc.metadata.get('format', 'Desconocido')
            metadata['is_pdfa'] = 'pdfa' in str(doc.metadata).lower()
            
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            logging.error(f"Error procesando {pdf_path.name}: {e}")
            return None, None, str(e)
            
        return text, metadata, None

    def get_cif_context(self, text, cif):
        """Busca el CIF en el texto original (no normalizado) y devuelve su contexto"""
        if not cif: return ""
        # Regex flexible para encontrar el CIF con posibles separadores
        pattern = "".join([f"{re.escape(c)}[\\s\\.-]*" for c in cif]).rstrip("[\\s\\.-]*")
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end].replace('\n', ' ')
            return f"...{context}..."
        return ""

    def parse_fields(self, text, doc=None, pdf_path=None):
        """Extrae campos mediante plantillas (si existen), Claude API o regex"""
        # --- NUEVO: Verificación de si es FACTURA ---
        keywords = ["FACTURA", "INVOICE", "ALBARAN", "CREDIT NOTE"]
        if not any(k in text.upper() for k in keywords):
            logging.warning(f"No se detectaron palabras clave de factura en {pdf_path.name if pdf_path else 'documento'}")
            return {"status": "ERROR: No es factura", "extraction_method": "FAILED"}

        # 1. Identificar CIF para ver si hay plantilla
        # Limpieza básica para regex pero sin normalizar el 'ES' aquí todavía
        clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
        cifs = re.findall(REGEX_CIF, clean_text)
        
        # Filtrar duplicados y el CIF de JOFEG
        unique_cifs = [c for c in dict.fromkeys(cifs) if c != JOFEG_CIF and c != "ES" + JOFEG_CIF]

        # --- NUEVO: Fallback agresivo para PDFs con texto basura (OCR malo) ---
        # Si no hay CIFs en el texto, mirar si el NOMBRE DEL ARCHIVO contiene un CIF conocido
        if not unique_cifs and pdf_path:
            filename = Path(pdf_path).name.upper()
            for known_cif in self.templates.keys():
                if known_cif in filename:
                    unique_cifs = [known_cif]
                    logging.info(f"Fallback: CIF {known_cif} encontrado en el nombre del archivo (Texto basura détectado)")
                    break

        # BUSCAR PLANTILLA O ERP: Probar todos los CIFs detectados para elegir el mejor
        primary_cif = None
        raw_cif = None
        
        # Prioridad 1: CIF con Plantilla
        for cif in unique_cifs:
            norm = self.normalize_id(cif)
            if norm in self.templates:
                primary_cif = norm
                raw_cif = cif
                logging.info(f"Prioridad 1: Coincidencia por PLANTILLA para {cif}")
                break
        
        # Prioridad 2: CIF con ERP (si no hay plantilla arriba)
        if not primary_cif:
            for cif in unique_cifs:
                norm = self.normalize_id(cif)
                if not self.suppliers[self.suppliers['CIF_NORM'] == norm].empty:
                    primary_cif = norm
                    raw_cif = cif
                    logging.info(f"Prioridad 2: Coincidencia por ERP para {cif}")
                    break
            
        # Prioridad 3: Primer CIF encontrado (si nada más sirve)
        if not raw_cif and unique_cifs:
            raw_cif = unique_cifs[0]
            primary_cif = self.normalize_id(raw_cif)
            logging.info(f"Prioridad 3: Usando primer CIF detectado: {raw_cif}")

        logging.info(f"Elegido: {raw_cif} (Normalizado: {primary_cif}) de entre {unique_cifs}")

        # Inicializar resultados con detección básica
        results = {
            "supplier_tax_id": raw_cif,
            "all_detected_ids": ", ".join(unique_cifs),
            "invoice_number": None,
            "invoice_date": None,
            "base_imponible": None,
            "iva_importe": None,
            "total_amount": None,
            "currency": "EUR" if "€" in text or "EUR" in text.upper() else "N/A",
            "extraction_method": "REGEX",
            "status": "OK"
        }

        # 2. Intentar usar PLANTILLA ZONAL
        if primary_cif and primary_cif in self.templates and doc:
            logging.info(f"Usando plantilla para CIF: {primary_cif}")
            template = self.templates[primary_cif]
            results["extraction_method"] = "TEMPLATE"
            page = doc[0]
            for field, info in template.get("fields", {}).items():
                rect = fitz.Rect(info["bbox"])
                field_text = page.get_text("text", clip=rect).strip()
                
                # REGLA DE CONFIANZA (Template Trust):
                # Si el campo es el CIF y está vacío (p.e. imagen sombreada), heredar de la plantilla
                if field == "supplier_tax_id" and not field_text:
                    logging.info(f"CIF vacío en zona de plantilla. Usando CIF de plantilla: {primary_cif}")
                    results[field] = primary_cif
                elif field == "supplier_tax_id" and field_text:
                    # Búsqueda inteligente dentro del cuadro
                    cif_pattern = r'[A-Z]?[0-9]{8}[A-Z]?'
                    matches = re.findall(cif_pattern, self.normalize_id(field_text))
                    results[field] = matches[0] if matches else field_text
                else:
                    results[field] = field_text

        # 3. MATCHING CON MAESTRO ERP (Prioridad 1: CIF de resultados, Prioridad 2: CIFs detectados)
        final_cif = self.normalize_id(results["supplier_tax_id"])
        
        # Intentar buscar el proveedor en el ERP
        match_data = self.suppliers[self.suppliers['CIF_NORM'] == final_cif]
        
        if match_data.empty and unique_cifs:
            # Si el CIF de la plantilla/extracción no está en ERP, probar otros detectados
            for c in unique_cifs:
                norm_c = self.normalize_id(c)
                match_data = self.suppliers[self.suppliers['CIF_NORM'] == norm_c]
                if not match_data.empty:
                    final_cif = norm_c
                    results["supplier_tax_id"] = c
                    logging.info(f"Cambiando a CIF detectado con match ERP: {final_cif}")
                    break
        
        # Si sigue sin match ERP pero tenemos plantilla, permitir procesar con aviso
        if match_data.empty:
             if results["extraction_method"] == "TEMPLATE":
                 results["status"] = "OK (Proveedor no en ERP)"
                 logging.warning(f"Proveedor {results['supplier_tax_id']} detectado por plantilla pero no está en PROVEE.csv")
             else:
                 results["status"] = "NO_MATCH"

        # 3a. Si NO hay plantilla Y Claude API está disponible, usarlo
        elif (self.use_claude_api and 
              self.claude_extractor and 
              self.claude_as_fallback_only and 
              primary_cif not in self.templates and
              pdf_path):
            
            try:
                logging.info(f"Usando Claude API para {Path(pdf_path).name}")
                claude_results = self.claude_extractor.extract_from_pdf(pdf_path)
                
                if claude_results:
                    # Usar resultados de Claude
                    for key, value in claude_results.items():
                        if value:
                            results[key] = value
                    
                    logging.info(f"Claude API extrajo correctamente de {Path(pdf_path).name}")
                else:
                    logging.warning(f"Claude API no pudo extraer datos de {Path(pdf_path).name}")
            
            except Exception as e:
                logging.error(f"Error en Claude API para {Path(pdf_path).name}: {e}")

        # 4. Completar con REGEX los campos vacíos (último recurso)
        if not results["invoice_number"]:
            m = re.search(r'(?:FACTURA|INVOICE|RECIBO|Nº|FACT[\.\s])[\s:º]*([A-Z0-9\-/]+)', text, re.IGNORECASE)
            results["invoice_number"] = m.group(1) if m else None
        
        if not results["invoice_date"]:
            dates = re.findall(REGEX_DATE, text)
            results["invoice_date"] = dates[0] if dates else None
            
        if not results["total_amount"]:
            amounts = re.findall(REGEX_AMOUNT, text)
            results["total_amount"] = amounts[-1] if amounts else None

        if not results["base_imponible"]:
            m = re.search(REGEX_BASE_LABEL, text)
            results["base_imponible"] = m.group(1) if m else None

        if not results["iva_importe"]:
            m = re.search(REGEX_IVA_LABEL, text)
            results["iva_importe"] = m.group(1) if m else None

        return results

    def _cleanup_stale_data(self, current_pdf_files):
        """Elimina del Estado y del Excel los archivos que ya no existen en disco"""
        current_paths = {str(p) for p in current_pdf_files}
        
        # 1. Limpiar State (JSON)
        initial_state_count = len(self.state)
        # Identificar claves que no están en los paths actuales
        # Nota: las claves en state son str(absolute_path)
        keys_to_remove = [k for k in self.state if k not in current_paths]
        
        for k in keys_to_remove:
            del self.state[k]
        
        if len(self.state) < initial_state_count:
            self._save_state()
            logging.info(f"Limpieza de Estado: Se eliminaron {initial_state_count - len(self.state)} entradas obsoletas.")
            
        # 2. Limpiar Excel
        if os.path.exists(OUTPUT_XLSX):
            try:
                df = pd.read_excel(OUTPUT_XLSX)
                initial_rows = len(df)
                
                # Filtrar solo las que existen
                # Aseguramos que file_path sea string para comparar
                df_clean = df[df['file_path'].astype(str).isin(current_paths)]
                
                if len(df_clean) < initial_rows:
                    df_clean.to_excel(OUTPUT_XLSX, index=False, engine='openpyxl')
                    logging.info(f"Limpieza de Excel: Se eliminaron {initial_rows - len(df_clean)} filas obsoletas.")
            except Exception as e:
                logging.error(f"Error limpiando Excel: {e}")

    def process_all(self):
        results = []
        if not os.path.exists(INPUT_PDF_DIR):
            logging.error(f"Directorio de entrada no existe: {INPUT_PDF_DIR}")
            return

        pdf_files = list(Path(INPUT_PDF_DIR).glob("**/*.pdf"))
        logging.info(f"Analizando {len(pdf_files)} archivos en {INPUT_PDF_DIR}")

        # LIMPIEZA: Eliminar registros de archivos que ya no existen
        self._cleanup_stale_data(pdf_files)

        # Cargar estados previos del Excel para forzar reprocesamiento de errores
        previous_statuses = {}
        if os.path.exists(OUTPUT_XLSX):
            try:
                df_prev = pd.read_excel(OUTPUT_XLSX)
                # Crear diccionario {file_path: status}
                previous_statuses = dict(zip(df_prev['file_path'].astype(str), df_prev['status']))
            except:
                pass

        for pdf_path in pdf_files:
            fingerprint = self.get_file_fingerprint(pdf_path)
            file_key = str(pdf_path)

            # Incremental: Saltamos si ya está procesado y no ha cambiado
            # EXCEPCIÓN: Si el estado previo fue NO_MATCH o ERROR, reprocesamos SIEMPRE
            prev_status = previous_statuses.get(file_key, "UNKNOWN")
            force_reprocess = (prev_status in ["NO_MATCH", "ERROR"])
            
            if not force_reprocess and file_key in self.state and self.state[file_key] == fingerprint:
                continue

            row = {
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "modified_datetime": datetime.fromtimestamp(os.path.getmtime(pdf_path)).isoformat(),
                "guid": hashlib.sha256(str(pdf_path).encode()).hexdigest()[:12],
                "status": "OK",
                "error": ""
            }

            text, meta, err = self.extract_idp_data(pdf_path)
            if err:
                row.update({"status": "ERROR", "error": err})
                results.append(row)
                continue

            # Necesitamos el documento abierto para el parseo por coordenadas
            doc = fitz.open(pdf_path)
            fields = self.parse_fields(text, doc, pdf_path=pdf_path)
            doc.close()
            
            row.update(fields)
            row.update({
                "pages": meta['pages'],
                "is_pdfa_compliant": meta['is_pdfa'],
                "text_preview": text[:2000].replace("\n", " "),
                "text_len": len(text)
            })

            # Matching ERP por CIF
            cif_norm = self.normalize_id(fields.get("supplier_tax_id", ""))
            match = self.suppliers[self.suppliers['CIF_NORM'] == cif_norm]
            
            # Contexto para depuración
            row["match_debug"] = self.get_cif_context(text, fields.get("supplier_tax_id", ""))

            if not match.empty:
                row.update({
                    "supplier_name_erp": match.iloc[0]['NOMBRE'],
                    "supplier_account": match.iloc[0]['CUENTA'],
                    "match_method": "CIF",
                    "match_score": 100
                    # El status ya viene como "OK" de parse_fields
                })
            else:
                row.update({
                    "supplier_name_erp": "",
                    "supplier_account": "",
                    "match_method": "NONE",
                    "match_score": 0
                })
                
                # REGLA ORO: Si parse_fields ya decidió que es un éxito (por plantilla), NO degradar a NO_MATCH
                if fields.get("status", "").startswith("OK"):
                    logging.info(f"Manteniendo status {fields['status']} (Template detected) para {pdf_path.name}")
                else:
                    row["status"] = "NO_MATCH"
                    logging.warning(f"NO_MATCH: No se encontró proveedor para CIF {fields.get('supplier_tax_id')} en {pdf_path.name}")

            results.append(row)
            self.state[file_key] = fingerprint

        if results:
            self.export(results)
            self._save_state()
            logging.info(f"Procesado finalizado. {len(results)} registros nuevos/actualizados.")
        else:
            logging.info("No hay cambios detectados desde la última ejecución.")

    def export(self, data):
        # Sanitizar datos para Excel (eliminar caracteres de control)
        import string
        ILLEGAL_CHARACTERS_RE = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]')
        
        for row in data:
            for key, value in row.items():
                if isinstance(value, str):
                    row[key] = ILLEGAL_CHARACTERS_RE.sub('', value)
        
        df_new = pd.DataFrame(data)
        if os.path.exists(OUTPUT_XLSX):
            try:
                df_old = pd.read_excel(OUTPUT_XLSX)
                df_final = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates(subset=['file_path'], keep='last')
            except:
                df_final = df_new
        else:
            df_final = df_new
            
        df_final.to_excel(OUTPUT_XLSX, index=False, engine='openpyxl')
        logging.info(f"Excel actualizado en: {OUTPUT_XLSX}")

if __name__ == "__main__":
    processor = JofegIDPProcessor()
    processor.process_all()
