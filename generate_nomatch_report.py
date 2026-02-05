import pandas as pd
import re
from datetime import datetime
from pathlib import Path

def is_suspicious_cif(cif):
    """Detecta CIFs que parecen mal formados o sospechosos"""
    if not cif or pd.isna(cif):
        return True
    
    cif = str(cif).upper()
    
    # Patrones sospechosos
    suspicious_patterns = [
        r'^\d{8}$',  # Solo 8 dígitos sin letra
        r'^[A-Z]{2,}$',  # Solo letras
        r'.*\d{4}202[0-9].*',  # Contiene año (ej: 20260128)
        r'^[0-9]{10,}',  # Más de 9 dígitos seguidos
        r'[A-Z]\d{2}[^0-9]',  # Formato muy corto
    ]
    
    for pattern in suspicious_patterns:
        if re.match(pattern, cif):
            return True
    
    return False

def analyze_nomatch_errors():
    """Genera reporte mejorado con priorización inteligente"""
    
    # Leer el Excel principal
    df = pd.read_excel('Resumen_Facturas_IDP.xlsx')
    
    # Filtrar solo los NO_MATCH
    no_match = df[df['status'] == 'NO_MATCH'].copy()
    
    if len(no_match) == 0:
        print("✅ No hay facturas sin match. Todos los CIFs fueron encontrados.")
        return
    
    # ANÁLISIS DE PRIORIDAD
    # Contar frecuencia de cada CIF
    cif_counts = no_match['supplier_tax_id'].value_counts().to_dict()
    
    # Añadir columnas de análisis
    no_match['frecuencia_proveedor'] = no_match['supplier_tax_id'].map(cif_counts)
    no_match['cif_sospechoso'] = no_match['supplier_tax_id'].apply(is_suspicious_cif)
    
    # Calcular prioridad (más alta = más urgente entrenar)
    # Prioridad = frecuencia * peso_validez
    no_match['prioridad'] = no_match.apply(
        lambda row: row['frecuencia_proveedor'] * (0.5 if row['cif_sospechoso'] else 1.0),
        axis=1
    )
    
    # Preparar datos para el reporte
    report = no_match[[
        'file_name',
        'file_path',
        'supplier_tax_id',
        'invoice_number',
        'invoice_date',
        'base_imponible',
        'iva_importe',
        'total_amount',
        'frecuencia_proveedor',
        'cif_sospechoso',
        'prioridad',
        'match_debug',
        'all_detected_ids'
    ]].copy()
    
    # Renombrar columnas para mayor claridad
    report.columns = [
        'Archivo PDF',
        'Ruta Completa',
        'CIF Detectado',
        'Nº Factura',
        'Fecha Factura',
        'Base Imponible',
        'Cuota IVA',
        'Importe Total',
        'Frecuencia',
        'CIF Sospechoso',
        'Prioridad',
        'Contexto (donde aparece el CIF)',
        'Todos los CIFs detectados'
    ]
    
    # Ordenar por prioridad (descendente)
    report = report.sort_values('Prioridad', ascending=False)
    
    # Generar nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'Reporte_CIFs_NoEncontrados_{timestamp}.xlsx'
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        report.to_excel(writer, sheet_name='CIFs No Encontrados', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['CIFs No Encontrados']
        worksheet.column_dimensions['A'].width = 35  # Archivo PDF
        worksheet.column_dimensions['B'].width = 50  # Ruta Completa
        worksheet.column_dimensions['C'].width = 18  # CIF
        worksheet.column_dimensions['D'].width = 20  # Nº Factura
        worksheet.column_dimensions['E'].width = 15  # Fecha
        worksheet.column_dimensions['F'].width = 15  # Base
        worksheet.column_dimensions['G'].width = 15  # IVA
        worksheet.column_dimensions['H'].width = 15  # Total
        worksheet.column_dimensions['I'].width = 12  # Frecuencia
        worksheet.column_dimensions['J'].width = 15  # Sospechoso
        worksheet.column_dimensions['K'].width = 10  # Prioridad
        worksheet.column_dimensions['L'].width = 60  # Contexto
        worksheet.column_dimensions['M'].width = 30  # Todos los CIFs
        
        # Aplicar formato condicional para CIFs sospechosos
        from openpyxl.styles import PatternFill
        yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        
        for idx, row in report.iterrows():
            if row['CIF Sospechoso']:  # CIF Sospechoso = True
                worksheet[f'C{idx+2}'].fill = yellow_fill
                worksheet[f'J{idx+2}'].fill = yellow_fill
        
        # Crear resumen por CIF con recomendaciones
        summary = no_match.groupby('supplier_tax_id').agg({
            'file_name': 'count',
            'cif_sospechoso': 'first',
            'prioridad': 'first'
        }).reset_index()
        summary.columns = ['CIF', 'Cantidad Facturas', 'Sospechoso', 'Prioridad']
        summary = summary.sort_values('Prioridad', ascending=False)
        
        # Añadir recomendación
        def get_recommendation(row):
            if row['Sospechoso']:
                return 'REVISAR - Posible error de detección'
            elif row['Cantidad Facturas'] >= 3:
                return 'ALTA PRIORIDAD - Crear plantilla'
            elif row['Cantidad Facturas'] >= 2:
                return 'MEDIA PRIORIDAD - Considerar plantilla'
            else:
                return 'BAJA PRIORIDAD - Validar manualmente'
        
        summary['Recomendación'] = summary.apply(get_recommendation, axis=1)
        
        summary.to_excel(writer, sheet_name='Resumen y Recomendaciones', index=False)
        worksheet2 = writer.sheets['Resumen y Recomendaciones']
        worksheet2.column_dimensions['A'].width = 18
        worksheet2.column_dimensions['B'].width = 18
        worksheet2.column_dimensions['C'].width = 12
        worksheet2.column_dimensions['D'].width = 12
        worksheet2.column_dimensions['E'].width = 40
        
        # Colorear recomendaciones
        from openpyxl.styles import Font
        red_font = Font(color="FF0000", bold=True)
        orange_font = Font(color="FF8C00", bold=True)
        green_font = Font(color="008000")
        
        for idx, row in summary.iterrows():
            if 'REVISAR' in str(row['Recomendación']):
                worksheet2[f'E{idx+2}'].font = red_font
            elif 'ALTA' in str(row['Recomendación']):
                worksheet2[f'E{idx+2}'].font = red_font
            elif 'MEDIA' in str(row['Recomendación']):
                worksheet2[f'E{idx+2}'].font = orange_font
            else:
                worksheet2[f'E{idx+2}'].font = green_font
    
    # Generar estadísticas
    print(f"📊 REPORTE GENERADO: {output_file}")
    print(f"\n📈 Estadísticas:")
    print(f"   - Total de facturas sin match: {len(no_match)}")
    print(f"   - CIFs únicos no encontrados: {no_match['supplier_tax_id'].nunique()}")
    print(f"   - CIFs sospechosos (posibles errores): {no_match['cif_sospechoso'].sum()}")
    
    print(f"\n🎯 RECOMENDACIONES PRIORITARIAS:")
    high_priority = summary[summary['Recomendación'].str.contains('ALTA|REVISAR')].head(5)
    for idx, row in high_priority.iterrows():
        print(f"   - {row['CIF']:15s} → {row['Cantidad Facturas']:2d} facturas | {row['Recomendación']}")
    
    print(f"\n✅ Abre el archivo '{output_file}' para ver el detalle completo.")
    
    return output_file

if __name__ == "__main__":
    analyze_nomatch_errors()
