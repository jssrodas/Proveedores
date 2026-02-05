import pandas as pd

# Leer el reporte generado
df_report = pd.read_excel('Reporte_CIFs_NoEncontrados_20260205_165103.xlsx', sheet_name='CIFs No Encontrados')
df_summary = pd.read_excel('Reporte_CIFs_NoEncontrados_20260205_165103.xlsx', sheet_name='Resumen por CIF')

print("="*80)
print("📊 REPORTE DE CIFs NO ENCONTRADOS EN EL MAESTRO PROVEE.CSV")
print("="*80)

print(f"\n📈 ESTADÍSTICAS GENERALES:")
print(f"   - Total de facturas sin match: {len(df_report)}")
print(f"   - CIFs únicos no encontrados: {len(df_summary)}")

print(f"\n🔝 TOP 10 CIFs MÁS FRECUENTES:")
print("-" * 60)
for idx, row in df_summary.head(10).iterrows():
    print(f"   {idx+1}. {row['CIF']:15s} → {row['Cantidad de Facturas']:2d} factura(s)")

print(f"\n📄 PRIMERAS 10 FACTURAS DEL REPORTE:")
print("-" * 80)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 40)

for idx, row in df_report.head(10).iterrows():
    print(f"\n{idx+1}. Archivo: {row['Archivo PDF']}")
    print(f"   CIF: {row['CIF Detectado']}")
    print(f"   Factura: {row['Nº Factura']} | Fecha: {row['Fecha Factura']} | Importe: {row['Importe Total']}")
    if pd.notna(row['Contexto (donde aparece el CIF)']):
        context = str(row['Contexto (donde aparece el CIF)'])[:80]
        print(f"   Contexto: {context}")

print("\n" + "="*80)
print(f"✅ Archivo completo: Reporte_CIFs_NoEncontrados_20260205_165103.xlsx")
print("="*80)
