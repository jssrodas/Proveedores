
import json
import os
from datetime import datetime

templates_path = r"c:\Proyectos\Proveedores\templates.json"
log_path = r"c:\Proyectos\Proveedores\idp_processor.log"

print(f"--- DIAGNÓSTICO {datetime.now()} ---")

if os.path.exists(templates_path):
    with open(templates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"templates.json: {len(data)} claves.")
        print(f"Claves: {list(data.keys())}")
else:
    print("templates.json NO EXISTE.")

if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"idp_processor.log: {len(lines)} líneas.")
        print("Últimas 20 líneas:")
        for line in lines[-20:]:
            print(line.strip())
else:
    print("idp_processor.log NO EXISTE.")
