"""
Script de prueba para verificar la configuración de Claude API
"""

import sys
from pathlib import Path

def test_api_configuration():
    """Verifica que la API Key está configurada correctamente"""
    print("="*60)
    print("TEST DE CONFIGURACIÓN - Claude API")
    print("="*60)
    
    # 1. Verificar archivo .env
    print("\n[1] Verificando archivo .env...")
    env_file = Path(".env")
    if env_file.exists():
        print("    ✅ Archivo .env encontrado")
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'ANTHROPIC_API_KEY' in content and 'sk-ant-api03' in content:
                print("    ✅ API Key configurada")
            else:
                print("    ❌ API Key no encontrada en .env")
                return False
    else:
        print("    ❌ Archivo .env no encontrado")
        return False
    
    # 2. Verificar import de anthropic
    print("\n[2] Verificando librería anthropic...")
    try:
        import anthropic
        print(f"    ✅ Librería anthropic instalada (v{anthropic.__version__})")
    except ImportError as e:
        print(f"    ❌ Error: {e}")
        return False
    
    # 3. Verificar extractor
    print("\n[3] Verificando módulo claude_extractor...")
    try:
        from claude_extractor import ClaudeIDPExtractor
        extractor = ClaudeIDPExtractor()
        print("    ✅ ClaudeIDPExtractor inicializado correctamente")
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False
    
    # 4. Verificar estimación de costes
    print("\n[4] Estimación de costes...")
    est = extractor.estimate_cost(10)
    print(f"    📊 Para 10 facturas:")
    print(f"       - Coste total: ${est['total_cost_usd']:.2f} USD")
    print(f"       - Coste por factura: ${est['cost_per_invoice_usd']:.3f} USD")
    
    # 5. Test real (opcional)
    print("\n[5] Test con factura real...")
    input_dir = Path(r"X:\Facts_Proveedor")
    if input_dir.exists():
        pdfs = list(input_dir.glob("*.pdf"))
        if pdfs:
            test_pdf = pdfs[0]
            print(f"    📄 Probando con: {test_pdf.name}")
            
            try:
                result = extractor.extract_from_pdf(test_pdf)
                if result:
                    print("    ✅ Extracción exitosa:")
                    print(f"       - CIF: {result.get('supplier_tax_id')}")
                    print(f"       - Nº Factura: {result.get('invoice_number')}")
                    print(f"       - Total: {result.get('total_amount')}")
                    print(f"       - Método: {result.get('extraction_method')}")
                    print(f"       - Confianza: {result.get('confidence')}")
                else:
                    print("    ⚠️  No se pudieron extraer datos")
            except Exception as e:
                print(f"    ❌ Error en extracción: {e}")
        else:
            print("    ⚠️  No hay PDFs para probar")
    else:
        print("    ⚠️  Directorio X:\\Facts_Proveedor no accesible")
    
    print("\n" + "="*60)
    print("✅ CONFIGURACIÓN COMPLETADA CORRECTAMENTE")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_api_configuration()
    sys.exit(0 if success else 1)
