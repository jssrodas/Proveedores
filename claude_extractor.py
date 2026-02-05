"""
Módulo de extracción inteligente usando Claude API con Vision
Este módulo se usa como FALLBACK cuando no hay plantillas para un proveedor
"""

import os
import base64
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# Cargar variables de entorno
load_dotenv()

class ClaudeIDPExtractor:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada en .env")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-haiku-20240307"  # Modelo económico con Vision
        
    def extract_from_pdf(self, pdf_path, max_pages=3):
        """
        Extrae datos de factura usando Claude Vision
        
        Args:
            pdf_path: Ruta al PDF
            max_pages: Número máximo de páginas a analizar (para controlar costes)
        
        Returns:
            dict con campos extraídos
        """
        try:
            # Convertir PDF a imágenes
            images = self._pdf_to_images(pdf_path, max_pages)
            
            # Preparar prompt especializado
            prompt = self._build_extraction_prompt()
            
            # Preparar contenido del mensaje con imágenes
            content = []
            for img_data in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_data
                    }
                })
            
            content.append({
                "type": "text",
                "text": prompt
            })
            
            # Llamar a Claude API
            logging.info(f"Llamando a Claude API para {Path(pdf_path).name}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )
            
            # Parsear respuesta JSON
            result_text = response.content[0].text
            result = json.loads(result_text)
            
            logging.info(f"Claude API extrajo: CIF={result.get('supplier_tax_id')}")
            
            return {
                "supplier_tax_id": result.get('supplier_tax_id'),
                "invoice_number": result.get('invoice_number'),
                "invoice_date": result.get('invoice_date'),
                "base_imponible": result.get('base_imponible'),
                "iva_importe": result.get('iva_importe'),
                "total_amount": result.get('total_amount'),
                "currency": result.get('currency', 'EUR'),
                "extraction_method": "CLAUDE_API",
                "confidence": result.get('confidence', 'medium')
            }
            
        except Exception as e:
            logging.error(f"Error en Claude API para {pdf_path}: {e}")
            return None
    
    def _pdf_to_images(self, pdf_path, max_pages=3):
        """Convierte páginas del PDF a imágenes base64"""
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        images = []
        doc = fitz.open(pdf_path)
        
        num_pages = len(doc)
        
        # Estrategia de selección de páginas:
        # Si hay pocas páginas, procesar todas.
        # Si hay muchas, priorizar la Primera (cabecera) y las Últimas (totales).
        if num_pages <= max_pages:
            page_indices = range(num_pages)
        else:
            # Siempre la primera página
            page_indices = [0]
            # Y las últimas (max_pages - 1) páginas
            remaining_slots = max_pages - 1
            if remaining_slots > 0:
                start_from = max(1, num_pages - remaining_slots)
                page_indices.extend(range(start_from, num_pages))
            
            # Asegurar orden y unicidad
            page_indices = sorted(list(set(page_indices)))
            
        logging.info(f"Procesando páginas {page_indices} de {num_pages} totales para {Path(pdf_path).name}")
        
        for page_num in page_indices:
            page = doc[page_num]
            
            # Renderizar página a imagen (300 DPI para buena calidad)
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            
            # Convertir a PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convertir a base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            images.append(img_base64)
        
        doc.close()
        return images
    
    def _build_extraction_prompt(self):
        """Construye el prompt optimizado para extracción de facturas españolas"""
        return """Analiza esta factura y extrae los siguientes datos en formato JSON:

IMPORTANTE:
- Busca el CIF/NIF del PROVEEDOR/EMISOR de la factura (NO del cliente)
- IGNORA explícitamente el CIF de cliente: A28346245 o ESA28346245 (JOFEG)
- El CIF/NIF español tiene formato: letra + 8 dígitos + letra/dígito (ej: A12345678) o 8 dígitos + letra (ej: 12345678A)
- Los importes pueden usar punto o coma como separador decimal
- La fecha puede estar en varios formatos (DD/MM/YYYY, DD-MM-YYYY, etc.)

Devuelve SOLO un JSON válido con esta estructura exacta:
{
    "supplier_tax_id": "CIF o NIF del proveedor/emisor",
    "invoice_number": "Número de factura",
    "invoice_date": "Fecha de la factura",
    "base_imponible": "Base imponible sin IVA",
    "iva_importe": "Importe del IVA",
    "total_amount": "Importe total con IVA",
    "currency": "EUR u otra moneda",
    "confidence": "high|medium|low según tu confianza en los datos"
}

Si algún campo no está visible o no estás seguro, usa null en ese campo.
NO añadas explicaciones, SOLO el JSON."""

    def estimate_cost(self, num_invoices, pages_per_invoice=3):
        """
        Estima el coste aproximado de procesar facturas
        
        Args:
            num_invoices: Número de facturas a procesar
            pages_per_invoice: Páginas promedio por factura
        
        Returns:
            dict con estimación de costes
        """
        # Costes aproximados Claude 3.5 Sonnet (Febrero 2024)
        INPUT_COST_PER_1K = 0.003   # $3 por millón de tokens
        OUTPUT_COST_PER_1K = 0.015  # $15 por millón de tokens
        
        # Estimaciones conservadoras
        TOKENS_PER_IMAGE = 1500  # Una imagen a 300 DPI ~1500 tokens
        TOKENS_PER_RESPONSE = 500  # Respuesta JSON ~500 tokens
        
        total_input_tokens = num_invoices * pages_per_invoice * TOKENS_PER_IMAGE
        total_output_tokens = num_invoices * TOKENS_PER_RESPONSE
        
        input_cost = (total_input_tokens / 1000) * INPUT_COST_PER_1K
        output_cost = (total_output_tokens / 1000) * OUTPUT_COST_PER_1K
        total_cost = input_cost + output_cost
        
        return {
            "num_invoices": num_invoices,
            "total_cost_usd": round(total_cost, 2),
            "cost_per_invoice_usd": round(total_cost / num_invoices, 3),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }


# Función de utilidad para testing
def test_extraction(pdf_path):
    """Prueba la extracción en un PDF específico"""
    extractor = ClaudeIDPExtractor()
    result = extractor.extract_from_pdf(pdf_path)
    
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Error en la extracción")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_extraction(sys.argv[1])
    else:
        # Estimación de costes
        extractor = ClaudeIDPExtractor()
        
        print("\n" + "="*60)
        print("ESTIMACIÓN DE COSTES - Claude API")
        print("="*60)
        
        scenarios = [
            (10, "10 facturas (prueba)"),
            (50, "50 facturas (mensual pequeño)"),
            (100, "100 facturas (mensual medio)"),
            (500, "500 facturas (mensual grande)")
        ]
        
        for num, desc in scenarios:
            est = extractor.estimate_cost(num)
            print(f"\n{desc}:")
            print(f"  Coste total: ${est['total_cost_usd']:.2f} USD")
            print(f"  Coste por factura: ${est['cost_per_invoice_usd']:.3f} USD")
