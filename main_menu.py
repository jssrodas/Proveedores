
import os
import sys
import subprocess
from pathlib import Path

# Configuración de Rutas
BASE_DIR = Path(r"c:\Proyectos\Proveedores")
INPUT_DIR = Path(r"X:\Facts_Proveedor")
LOG_FILE = BASE_DIR / "idp_processor.log"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 60)
    print("      JOFEG IDP - SISTEMA DE PROCESAMIENTO DE FACTURAS")
    print("=" * 60)

def run_processor():
    print("\n[1] Iniciando Procesamiento Completo de Facturas...")
    from jofeg_idp_processor import JofegIDPProcessor
    try:
        processor = JofegIDPProcessor()
        processor.process_all()
        print("\n[OK] Proceso finalizado correctamente.")
    except Exception as e:
        print(f"\n[ERROR] Error durante el procesamiento: {e}")
    input("\nPresiona Enter para volver al menú...")

def train_template():
    print("\n[2] Entrenamiento de Nuevas Plantillas")
    if not INPUT_DIR.exists():
        print(f"Error: El directorio {INPUT_DIR} no es accesible.")
        return

    pdfs = list(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print("No se encontraron archivos PDF en el directorio de entrada.")
        input("\nPresiona Enter para volver...")
        return

    print("\nSelecciona un fichero para entrenar:")
    for i, pdf in enumerate(pdfs):
        print(f"{i+1}. {pdf.name}")
    print("0. Cancelar")

    choice = input("\nOpción: ")
    if choice.isdigit() and 0 < int(choice) <= len(pdfs):
        selected_pdf = str(pdfs[int(choice)-1])
        # Ejecutamos el trainer como un subproceso para mantener el aislamiento
        subprocess.run([sys.executable, "jofeg_trainer.py", selected_pdf])
    else:
        print("Operación cancelada.")
    
    input("\nPresiona Enter para volver al menú...")

def manage_templates():
    print("\n[3] Gestión de Plantillas Existentes")
    TEMPLATES_PATH = BASE_DIR / "templates.json"
    if not TEMPLATES_PATH.exists():
        print("No hay plantillas registradas todavía.")
    else:
        import json
        with open(TEMPLATES_PATH, 'r') as f:
            templates = json.load(f)
        print(f"\nSe han encontrado {len(templates)} plantillas:")
        for cif, data in templates.items():
            fields = ", ".join(data.get("fields", {}).keys())
            print(f"- CIF: {cif} (Campos: {fields})")
            
    input("\nPresiona Enter para volver...")

def view_logs():
    print("\n[4] Últimas entradas del Log:")
    if not LOG_FILE.exists():
        print("No se ha generado ningún log todavía.")
    else:
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-15:]:  # Mostrar las últimas 15 líneas
                    print(line.strip())
        except Exception as e:
            print(f"Error leyendo el log: {e}")
            
    input("\nPresiona Enter para volver...")

def main():
    while True:
        clear_screen()
        print_header()
        print("1. Ejecutar Procesamiento de Facturas (Automático)")
        print("2. Entrenar Nuevo Proveedor (Manual/Zonal)")
        print("3. Ver Plantillas Registradas")
        print("4. Ver Log de Operaciones")
        print("0. Salir")
        print("-" * 60)
        
        choice = input("Selecciona una opción: ")
        
        if choice == "1":
            run_processor()
        elif choice == "2":
            train_template()
        elif choice == "3":
            manage_templates()
        elif choice == "4":
            view_logs()
        elif choice == "0":
            print("Saliendo del sistema...")
            break
        else:
            print("Opción no válida. Inténtalo de nuevo.")
            import time
            time.sleep(1)

if __name__ == "__main__":
    main()
