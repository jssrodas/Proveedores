
import fitz
from pathlib import Path

pdf_path = r"X:\Facts_Proveedor\Factura_1_260435.pdf"

if not Path(pdf_path).exists():
    # Intentar buscarlo en el directorio si la ruta exacta cambió
    root = r"X:\Facts_Proveedor"
    found = list(Path(root).glob("**/Factura_1_260435.pdf"))
    if found:
        pdf_path = str(found[0])
    else:
        print(f"ERROR: No se encuentra {pdf_path}")
        exit()

doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()
doc.close()

print(f"--- TEXTO DE {pdf_path} ---")
print(text[:2000]) # Primeros 2000 chars
print("--- FIN ---")
