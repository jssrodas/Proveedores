
from pathlib import Path
import os
import pandas as pd

input_dir = r"X:\Facts_Proveedor"
print(f"Listing {input_dir}:")
try:
    files = os.listdir(input_dir)
    print(f"Total entries: {len(files)}")
    pdfs = [f for f in files if f.lower().endswith('.pdf')]
    print(f"PDFs in os.listdir: {len(pdfs)}")
    if pdfs:
        print(f"First PDF: {pdfs[0]}")
except Exception as e:
    print(f"Error listing dir: {e}")

pdf_files = list(Path(input_dir).glob("*.pdf"))
print(f"Found {len(pdf_files)} PDFs with Path.glob(*.pdf)")
pdf_files_rec = list(Path(input_dir).glob("**/*.pdf"))
print(f"Found {len(pdf_files_rec)} PDFs with Path.glob(**/*.pdf)")

xlsx = r"c:\Proyectos\Proveedores\Resumen_Facturas_IDP_Local.xlsx"
if os.path.exists(xlsx):
    print(f"Excel exists: {xlsx}")
    try:
        df = pd.read_excel(xlsx)
        print("Columns:", df.columns.tolist())
        print(f"Rows: {len(df)}")
        print(df.head(5))
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print("Excel does NOT exist.")
