
import os
import time
from pathlib import Path
import logging
from jofeg_idp_processor import JofegIDPProcessor

# Config setup
logging.basicConfig(level=logging.INFO)

# Define paths (Production paths from jofeg_idp_processor)
BASE_DIR = Path(r"c:\Proyectos\Proveedores")
STATE_FILE = BASE_DIR / "processing_state.json"
EXCEL_FILE = BASE_DIR / "Resumen_Facturas_IDP.xlsx"

print("=== FORCING FULL REPROCESSING TO FIX EXCEL ===")

# 1. Delete State File (Forces re-reading all PDFs)
if STATE_FILE.exists():
    print(f"Deleting state file: {STATE_FILE}")
    try:
        os.remove(STATE_FILE)
    except Exception as e:
        print(f"Error checking state file: {e}")

# 2. Delete Excel File (Forces fresh write of columns)
if EXCEL_FILE.exists():
    print(f"Deleting Excel file: {EXCEL_FILE}")
    try:
        os.remove(EXCEL_FILE)
    except Exception as e:
        print(f"Error checking Excel file: {e}")
        # Try renaming if delete fails (e.g. file open)
        try:
            timestamp = int(time.time())
            os.rename(EXCEL_FILE, str(EXCEL_FILE) + f".bak{timestamp}")
            print("Renamed Excel instead of deleting.")
        except:
            print("Could not delete or rename Excel. Close it if open!")

# 3. Run Processor
print("Starting Processor...")
processor = JofegIDPProcessor()
processor.process_all()

print("=== DONE ===")
print(f"Please check: {EXCEL_FILE}")
