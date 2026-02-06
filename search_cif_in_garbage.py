
import fitz
import re

pdf_path = r"X:\Facts_Proveedor\Factura_1_260435.pdf"
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()
doc.close()

# Regex flexible para CIFs
REGEX_CIF = r'[ABCDEFGHJNPQRSUVW][0-9]{7}[A-Z0-9]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE]'

clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
cifs = re.findall(REGEX_CIF, clean_text)

print(f"CIFs encontrados en el texto: {cifs}")
