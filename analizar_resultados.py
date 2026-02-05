import pandas as pd

df = pd.read_excel('Resumen_Facturas_IDP.xlsx')

print("=" * 70)
print("RESUMEN DEL PROCESAMIENTO CON CLAUDE API")
print("=" * 70)

print(f"\nTotal facturas procesadas: {len(df)}")

print("\n--- POR MÉTODO DE EXTRACCIÓN ---")
print(df['extraction_method'].value_counts())

print("\n--- POR STATUS ---")
print(df['status'].value_counts())

# Detalles de Claude API
claude_df = df[df['extraction_method'] == 'CLAUDE_API']
print(f"\n--- DETALLES CLAUDE API ---")
print(f"Total facturas con Claude: {len(claude_df)}")
print(f"Claude OK: {len(claude_df[claude_df['status'] == 'OK'])}")
print(f"Claude NO_MATCH: {len(claude_df[claude_df['status'] == 'NO_MATCH'])}")

# Plantillas usadas
template_df = df[df['extraction_method'] == 'TEMPLATE']
print(f"\n--- PLANTILLAS ---")
print(f"Total con plantilla: {len(template_df)}")

# Regex
regex_df = df[df['extraction_method'] == 'REGEX']
print(f"\n--- REGEX (Fallback) ---")
print(f"Total con regex: {len(regex_df)}")
print(f"Regex OK: {len(regex_df[regex_df['status'] == 'OK'])}")
print(f"Regex NO_MATCH: {len(regex_df[regex_df['status'] == 'NO_MATCH'])}")

print("\n" + "=" * 70)
print("ANÁLISIS COMPLETADO")
print("=" * 70)
