"""
Script para ejecutar el procesamiento con Claude API y mostrar progreso
"""

from jofeg_idp_processor import JofegIDPProcessor
import logging

# Configurar logging para ver el progreso
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("=" * 70)
print("PROCESAMIENTO DE FACTURAS CON CLAUDE API")
print("=" * 70)
print("\nModo: Híbrido (Plantillas → Claude API → Regex)")
print("Modelo Claude: Haiku (económico y rápido)")
print("\nIniciando...\n")

# Crear procesador con Claude API activado
processor = JofegIDPProcessor(
    use_claude_api=True,
    claude_as_fallback_only=True
)

# Ejecutar procesamiento
processor.process_all()

print("\n" + "=" * 70)
print("PROCESAMIENTO COMPLETADO")
print("=" * 70)
print("\nRevisa el archivo: Resumen_Facturas_IDP.xlsx")
print("Busca la columna 'extraction_method' para ver qué usó Claude API")
