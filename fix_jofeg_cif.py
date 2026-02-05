import pandas as pd
import re

EXCEL_PATH = r"c:\Proyectos\Proveedores\Resumen_Facturas_IDP.xlsx"
JOFEG_CIFS = ["A28346245", "ESA28346245"]
REGEX_CIF = r'[ABCDEFGHJNPQRSUVW][0-9]{7}[A-Z0-9]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE]'

print(f"Abriendo {EXCEL_PATH}...")
df = pd.read_excel(EXCEL_PATH)

count_fixed = 0

for index, row in df.iterrows():
    cif_actual = str(row['supplier_tax_id']).strip().upper()
    
    if cif_actual in JOFEG_CIFS:
        print(f"Fila {index}: CIF incorrecto detectado ({cif_actual}) en {row['file_name']}")
        
        # Buscar alternativas en all_detected_ids
        all_ids = str(row['all_detected_ids']).split(',')
        candidates = [c.strip() for c in all_ids if c.strip() and c.strip() not in JOFEG_CIFS]
        
        # O intentar extraer de nuevo del text_preview si es necesario
        if not candidates and isinstance(row.get('text_preview'), str):
            candidates = re.findall(REGEX_CIF, row['text_preview'])
            candidates = [c for c in candidates if c not in JOFEG_CIFS]
            
        if candidates:
            new_cif = candidates[0]
            print(f"  -> Corregido a: {new_cif}")
            df.at[index, 'supplier_tax_id'] = new_cif
            df.at[index, 'status'] = 'NO_MATCH' # Asegurar que se revise si no estaba verificado
        else:
            print(f"  -> No se encontraron CIFs alternativos. Se deja vacío.")
            df.at[index, 'supplier_tax_id'] = None
            df.at[index, 'status'] = 'NO_MATCH'
            
        count_fixed += 1

if count_fixed > 0:
    print(f"\nGuardando correcciones ({count_fixed} registros)...")
    df.to_excel(EXCEL_PATH, index=False)
    print("✅ Excel actualizado correctamente.")
else:
    print("\nNo se encontraron registros con el CIF de JOFEG.")
