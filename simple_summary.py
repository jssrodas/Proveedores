import pandas as pd

# Leer ambas hojas
df_detail = pd.read_excel('Reporte_CIFs_NoEncontrados_20260205_165103.xlsx', sheet_name='CIFs No Encontrados')
df_summary = pd.read_excel('Reporte_CIFs_NoEncontrados_20260205_165103.xlsx', sheet_name='Resumen por CIF')

print("REPORTE DE CIFs NO ENCONTRADOS")
print("="*60)
print(f"Total facturas sin match: {len(df_detail)}")
print(f"CIFs unicos no encontrados: {len(df_summary)}")
print("\n")

print("TOP 10 CIFs MAS FRECUENTES:")
print("-"*60)
for idx, row in df_summary.head(10).iterrows():
    cif = str(row['CIF'])
    count = int(row['Cantidad de Facturas'])
    print(f"{idx+1:2d}. CIF: {cif:15s} --> {count:2d} factura(s)")

print("\n")
print("LISTA DE FACTURAS (primeras 15):")
print("-"*60)
for idx, row in df_detail.head(15).iterrows():
    archivo = str(row['Archivo PDF'])
    cif = str(row['CIF Detectado'])
    factura = str(row['Nº Factura']) if pd.notna(row['Nº Factura']) else 'N/A'
    
    print(f"{idx+1:2d}. {archivo}")
    print(f"    CIF: {cif} | Factura: {factura}")
