
import os
import fitz  # PyMuPDF
import json
from pathlib import Path

TEMPLATES_PATH = r"c:\Proyectos\Proveedores\templates.json"

class JofegTrainer:
    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self):
        if os.path.exists(TEMPLATES_PATH):
            with open(TEMPLATES_PATH, 'r') as f:
                return json.load(f)
        return {}

    def generate_mapping_image(self, pdf_path):
        """Genera un PDF/Imagen donde cada bloque de texto tiene un ID rojo"""
        doc = fitz.open(pdf_path)
        page = doc[0]  # Entrenamos con la primera página
        
        # Crear un nuevo documento para el 'mapa'
        out_doc = fitz.open()
        out_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        out_page.show_pdf_page(out_page.rect, doc, 0)
        
        blocks = page.get_text("blocks")
        mapping_data = []

        for i, b in enumerate(blocks):
            # b = (x0, y0, x1, y1, "texto", block_no, block_type)
            rect = fitz.Rect(b[:4])
            text = b[4].strip()
            
            # Dibujar recuadro y número
            out_page.draw_rect(rect, color=(1, 0, 0), width=0.5)
            # Fondo blanco para el número para que sea legible
            text_rect = fitz.Rect(rect.x0, rect.y0 - 10, rect.x0 + 15, rect.y0)
            out_page.draw_rect(text_rect, color=(1, 1, 1), fill=(1, 1, 1))
            out_page.insert_text((rect.x0, rect.y0), str(i), fontsize=8, color=(1, 0, 0))
            
            mapping_data.append({
                "id": i,
                "text": text,
                "bbox": b[:4] # Coordenadas relativas
            })

        output_map = Path(pdf_path).stem + "_MAPA.pdf"
        out_doc.save(output_map)
        out_doc.close()
        doc.close()
        
        print(f"\n[MAPA GENERADO]: Se ha creado '{output_map}'")
        print("Abriendo el mapa automáticamente para que veas los IDs numerados...")
        
        # Abrir el PDF automáticamente en Windows
        try:
            os.startfile(output_map)
        except Exception as e:
            print(f"No se pudo abrir el PDF automáticamente: {e}")
            print(f"Por favor, abre manualmente: {os.path.abspath(output_map)}")

        print("\nBusca en el PDF abierto los números que corresponden a cada campo.")
        return mapping_data

    def save_template(self, cif, mapping_data, selections):
        """Guarda la plantilla asociada a un CIF"""
        template = {
            "cif": cif,
            "fields": {}
        }
        
        for field_name, block_id in selections.items():
            block = next((b for b in mapping_data if b["id"] == block_id), None)
            if block:
                template["fields"][field_name] = {
                    "bbox": block["bbox"],
                    "text_hint": block["text"] # Usado como ancla de seguridad
                }
        
        self.templates[cif] = template
        with open(TEMPLATES_PATH, 'w') as f:
            json.dump(self.templates, f, indent=4)
        print(f"\n[PLANTILLA GUARDADA]: Registrada para el CIF {cif}")

if __name__ == "__main__":
    import sys
    trainer = JofegTrainer()
    
    # Ejemplo de uso rápido via CLI
    if len(sys.argv) < 2:
        print("Uso: python jofeg_trainer.py ruta_al_pdf.pdf")
    else:
        pdf_file = sys.argv[1]
        data = trainer.generate_mapping_image(pdf_file)
        
        print("\n--- ASIGNACIÓN DE CAMPOS ---")
        cif = input("Introduce el CIF del proveedor para esta plantilla: ").strip()
        
        selections = {}
        print("Introduce el ID del bloque para cada campo (deja vacío para omitir):")
        fields = ["invoice_number", "invoice_date", "base_imponible", "iva_importe", "total_amount"]
        
        for f in fields:
            val = input(f"ID para '{f}': ")
            if val.isdigit():
                selections[f] = int(val)
        
        if selections:
            trainer.save_template(cif, data, selections)
