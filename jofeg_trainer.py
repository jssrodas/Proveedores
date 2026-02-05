
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
        
        # Usamos 'dict' para obtener líneas individuales en lugar de bloques grandes
        page_dict = page.get_text("dict")
        mapping_data = []
        
        counter = 0
        
        for block in page_dict["blocks"]:
            if block["type"] == 0:  # Tipo 0 es texto
                for line in block["lines"]:
                    # Obtener bbox de la línea
                    bbox = line["bbox"]
                    rect = fitz.Rect(bbox)
                    
                    # Obtener texto de la línea (concatenando spans)
                    text = " ".join([span["text"] for span in line["spans"]]).strip()
                    
                    if not text:
                        continue
                        
                    # Dibujar recuadro y número
                    out_page.draw_rect(rect, color=(1, 0, 0), width=0.5)
                    
                    # Fondo blanco para el número para que sea legible
                    # Colocamos el ID un poco a la izquierda si hay espacio, o arriba si no
                    if rect.x0 > 20:
                        # Colocar a la izquierda
                        text_rect = fitz.Rect(rect.x0 - 18, rect.y0, rect.x0 - 2, rect.y1)
                        # Centrar verticalmente si la línea es alta
                        if text_rect.height > 10:
                            mid_y = (rect.y0 + rect.y1) / 2
                            text_rect.y0 = mid_y - 5
                            text_rect.y1 = mid_y + 5
                    else:
                        # Colocar arriba (fallback)
                        text_rect = fitz.Rect(rect.x0, max(0, rect.y0 - 10), rect.x0 + 15, rect.y0)
                         
                    out_page.draw_rect(text_rect, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    # Calcular posición del texto centrada en el recuadro
                    tx = text_rect.x0 + 2
                    ty = text_rect.y1 - 2 # Aproximación para baseline
                    
                    out_page.insert_text((tx, ty), str(counter), fontsize=7, color=(1, 0, 0))
                    
                    mapping_data.append({
                        "id": counter,
                        "text": text,
                        "bbox": bbox
                    })
                    counter += 1

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
        # Normalizar CIF para asegurar coincidencia (mismo método que jofeg_idp_processor)
        import re
        cif_key = re.sub(r'[^A-Z0-9]', '', str(cif).upper())
        
        template = {
            "cif": cif_key,
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
