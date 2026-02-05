
import fitz
import re
import os

pdf_path = r"C:\Users\Javierg\Documents\PA483_Factura.pdf"

def test_extraction(path):
    print(f"\n--- Probando Extracción en: {os.path.basename(path)} ---")
    try:
        doc = fitz.open(path)
        print(f"Páginas: {len(doc)}")
        print(f"Metadatos: {doc.metadata}")
        
        text = ""
        for page in doc:
            text += page.get_text()
        
        print("\n--- Vista Previa del Texto (500 chars) ---")
        print(text[:500])
        
        # Pruebas de Regex
        REGEX_CIF = r'[ABCDEFGHJNPQRSUVW][0-9]{7}[A-Z0-9]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE]'
        normalized_text = re.sub(r'[^A-Z0-9]', '', text.upper())
        cifs = re.findall(REGEX_CIF, normalized_text)
        print(f"\nCIFs Detectados (Normalizados): {cifs}")
        
        doc.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_extraction(pdf_path)
