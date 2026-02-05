from claude_extractor import ClaudeIDPExtractor
import traceback

print("Iniciando prueba detallada...")

try:
    ex = ClaudeIDPExtractor()
    print("Extractor creado correctamente")
    
    pdf_path = r'X:\Facts_Proveedor\0300600200457Cert.pdf'
    print(f"Procesando: {pdf_path}")
    
    result = ex.extract_from_pdf(pdf_path)
    
    if result:
        print("\n=== EXITO ===")
        print(f"CIF: {result.get('supplier_tax_id')}")
        print(f"Factura: {result.get('invoice_number')}")
        print(f"Total: {result.get('total_amount')}")
        print(f"Metodo: {result.get('extraction_method')}")
    else:
        print("\nNo se pudo extraer datos")
        
except Exception as e:
    print(f"\n=== ERROR COMPLETO ===")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
