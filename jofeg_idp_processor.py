
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
    def __init__(self):
        self.state = self._load_state()
        self.suppliers = self._load_suppliers()
        self.templates = self._load_templates()
        self._ensure_output_dir()

    def _load_templates(self):
        if os.path.exists(TEMPLATES_PATH):
            try:
                with open(TEMPLATES_PATH, 'r') as f:
                    return json.load(f)
            except:
                return {}
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
        return re.sub(r'[^A-Z0-9]', '', str(text).upper())

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

    def parse_fields(self, text, doc=None):
        """Extrae campos mediante plantillas (si existen) o regex"""
        # 1. Identificar CIF para ver si hay plantilla
        norm_text = self.normalize_id(text)
        cifs = re.findall(REGEX_CIF, norm_text)
        unique_cifs = list(dict.fromkeys(cifs))
        primary_cif = unique_cifs[0] if unique_cifs else None
        
        # Inicializar resultados con detección básica
        results = {
            "supplier_tax_id": primary_cif,
            "all_detected_ids": ", ".join(unique_cifs),
            "invoice_number": None,
            "invoice_date": None,
            "base_imponible": None,
            "iva_importe": None,
            "total_amount": None,
            "currency": "EUR" if "€" in text or "EUR" in text.upper() else "N/A",
            "extraction_method": "REGEX"
        }

        # 2. Intentar usar PLANTILLA ZONAL
        if primary_cif in self.templates and doc:
            template = self.templates[primary_cif]
            results["extraction_method"] = "TEMPLATE"
            page = doc[0]
            for field, info in template.get("fields", {}).items():
                rect = fitz.Rect(info["bbox"])
                val = page.get_text("text", clip=rect).strip()
                if val: results[field] = val

        # 3. Completar con REGEX los campos vacíos (mecanismo de respaldo)
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

    def process_all(self):
        results = []
        if not os.path.exists(INPUT_PDF_DIR):
            logging.error(f"Directorio de entrada no existe: {INPUT_PDF_DIR}")
            return

        pdf_files = list(Path(INPUT_PDF_DIR).glob("**/*.pdf"))
        logging.info(f"Analizando {len(pdf_files)} archivos en {INPUT_PDF_DIR}")

        for pdf_path in pdf_files:
            fingerprint = self.get_file_fingerprint(pdf_path)
            file_key = str(pdf_path)

            # Incremental: Saltamos si ya está procesado y no ha cambiado
            if file_key in self.state and self.state[file_key] == fingerprint:
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
            fields = self.parse_fields(text, doc)
            doc.close()
            
            row.update(fields)
            row.update({
                "pages": meta['pages'],
                "is_pdfa_compliant": meta['is_pdfa'],
                "text_preview": text[:2000].replace("\n", " "),
                "text_len": len(text)
            })

            # Matching ERP por CIF
            cif_norm = self.normalize_id(fields["supplier_tax_id"])
            match = self.suppliers[self.suppliers['CIF_NORM'] == cif_norm]
            
            # Contexto para depuración
            row["match_debug"] = self.get_cif_context(text, fields["supplier_tax_id"])

            if not match.empty:
                row.update({
                    "supplier_name_erp": match.iloc[0]['NOMBRE'],
                    "supplier_account": match.iloc[0]['CUENTA'],
                    "match_method": "CIF",
                    "match_score": 100
                })
            else:
                row.update({
                    "supplier_name_erp": "",
                    "supplier_account": "",
                    "match_method": "NONE",
                    "match_score": 0,
                    "status": "NO_MATCH"
                })
                logging.warning(f"NO_MATCH: No se encontró proveedor para CIF {fields['supplier_tax_id']} en {pdf_path.name}")

            results.append(row)
            self.state[file_key] = fingerprint

        if results:
            self.export(results)
            self._save_state()
            logging.info(f"Procesado finalizado. {len(results)} registros nuevos/actualizados.")
        else:
            logging.info("No hay cambios detectados desde la última ejecución.")

    def export(self, data):
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
