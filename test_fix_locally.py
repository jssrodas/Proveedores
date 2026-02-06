
import logging
import jofeg_idp_processor

# Configure logging
logging.basicConfig(level=logging.INFO)

# Override configuration to look at local directory
jofeg_idp_processor.INPUT_PDF_DIR = r"X:\Facts_Proveedor"
jofeg_idp_processor.OUTPUT_XLSX = r"c:\Proyectos\Proveedores\Resumen_Facturas_IDP_Local.xlsx"
# Ensure state path is consistent or separate so we don't ignore files "already processed" in production state
jofeg_idp_processor.STATE_PATH = r"c:\Proyectos\Proveedores\processing_state_local.json"

print(f"Processing files in {jofeg_idp_processor.INPUT_PDF_DIR}")

# Instanciar y procesar
processor = jofeg_idp_processor.JofegIDPProcessor(use_claude_api=True, claude_as_fallback_only=True)

# Forzar reprocesamiento borrando estado local si existe (opcional)
import os
if os.path.exists(jofeg_idp_processor.STATE_PATH):
    os.remove(jofeg_idp_processor.STATE_PATH)

processor.process_all()

print(f"Done. Check {jofeg_idp_processor.OUTPUT_XLSX}")
