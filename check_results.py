import pandas as pd

df = pd.read_excel('Resumen_Facturas_IDP.xlsx')
print(f'Total de registros procesados: {len(df)}')
print(f'Registros con match (encontrados en PROVEE.csv): {len(df[df["match_method"] != "NONE"])}')
print(f'Registros sin match (CIF no encontrado): {len(df[df["match_method"] == "NONE"])}')
print(f'\nEstados:')
print(df['status'].value_counts())
