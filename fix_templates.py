
import json
import re
import os

TEMPLATES_PATH = r"c:\Proyectos\Proveedores\templates.json"

def normalize_id(text):
    if not text: return ""
    norm = re.sub(r'[^A-Z0-9]', '', str(text).upper())
    if norm.startswith("ES") and len(norm) > 7:
        return norm[2:]
    return norm

def fix_templates():
    if not os.path.exists(TEMPLATES_PATH):
        print("No se encontró templates.json")
        return

    with open(TEMPLATES_PATH, 'r') as f:
        templates = json.load(f)

    new_templates = {}
    for key, data in templates.items():
        # Ignorar si la clave es un número pequeño (error de entrenamiento probable)
        if key.isdigit() and int(key) < 1000:
            print(f"Eliminando clave sospechosa: {key}")
            continue
        
        norm_key = normalize_id(key)
        if not norm_key:
            print(f"Eliminando clave vacía o inválida: {key}")
            continue

        if norm_key in new_templates:
            print(f"Fusionando/Reemplazando clave duplicada: {norm_key} (antes {key})")
        
        # Actualizar el CIF dentro de la data también
        data["cif"] = norm_key
        new_templates[norm_key] = data

    with open(TEMPLATES_PATH, 'w') as f:
        json.dump(new_templates, f, indent=4)
    print("Limpieza completada.")

if __name__ == "__main__":
    fix_templates()
