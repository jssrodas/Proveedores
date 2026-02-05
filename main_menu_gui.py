
import os
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, Listbox, Scrollbar
from pathlib import Path
import subprocess
import json
import logging
import pandas as pd

# Configuración de Rutas
BASE_DIR = Path(r"c:\Proyectos\Proveedores")
INPUT_DIR = Path(r"X:\Facts_Proveedor")
LOG_FILE = BASE_DIR / "idp_processor.log"
TEMPLATES_PATH = BASE_DIR / "templates.json"
EXCEL_OUTPUT = BASE_DIR / "Resumen_Facturas_IDP.xlsx"

class JofegIDPMenuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JOFEG IDP - Sistema de Procesamiento de Facturas")
        self.root.geometry("650x550")
        self.root.configure(padx=30, pady=20, bg="#f0f0f0")
        
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#0078D4", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(
            header_frame, 
            text="JOFEG IDP\nSistema de Procesamiento de Facturas", 
            font=("Arial", 16, "bold"),
            bg="#0078D4",
            fg="white",
            justify="center"
        )
        header_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Botones principales
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.pack(fill="both", expand=True)
        
        buttons = [
            ("🔄 Ejecutar Procesamiento de Facturas", self.run_processor, "#28a745"),
            ("🔍 Verificar Última Ejecución", self.verify_last_run, "#17a2b8"),
            ("📝 Entrenar Nuevo Proveedor", self.train_template, "#007bff"),
            ("⚠️ Entrenar desde Errores", self.train_from_errors, "#fd7e14"),
            ("📋 Ver Plantillas Registradas", self.manage_templates, "#6c757d"),
            ("📄 Ver Log de Operaciones", self.view_logs, "#ffc107"),
            ("❌ Salir", self.exit_app, "#dc3545")
        ]
        
        for i, (text, command, color) in enumerate(buttons):
            btn = tk.Button(
                btn_frame,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Arial", 10, "bold"),
                height=2,
                relief="raised",
                borderwidth=2,
                cursor="hand2"
            )
            btn.pack(fill="x", pady=6, ipady=3)
            
            # Efecto hover
            btn.bind("<Enter>", lambda e, b=btn: b.config(relief="sunken"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(relief="raised"))
        
        # Footer con información
        footer = tk.Label(
            self.root,
            text="Desarrollado para JOFEG © 2026",
            font=("Arial", 8),
            bg="#f0f0f0",
            fg="#6c757d"
        )
        footer.pack(side="bottom", pady=(10, 0))
    
    def run_processor(self):
        """Ejecuta el procesamiento completo de facturas"""
        if not INPUT_DIR.exists():
            messagebox.showerror(
                "Error de Ruta",
                f"El directorio de facturas no es accesible:\n{INPUT_DIR}\n\nVerifica que la unidad de red esté montada."
            )
            return
        
        # Eliminamos la confirmación previa para agilizar el proceso ("Hay demasiados mensajes")
        # response = messagebox.askyesno(...)
        
        try:
            from jofeg_idp_processor import JofegIDPProcessor
            
            # Ventana de progreso
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Procesando...")
            progress_window.geometry("500x300")
            progress_window.configure(padx=20, pady=20)
            
            label = tk.Label(
                progress_window,
                text="⏳ Procesamiento en curso...\n\nPor favor, espera mientras se procesan las facturas.",
                font=("Arial", 10),
                justify="center"
            )
            label.pack(pady=20)
            
            log_text = scrolledtext.ScrolledText(
                progress_window,
                width=60,
                height=12,
                font=("Consolas", 9),
                bg="#1e1e1e",
                fg="#00ff00"
            )
            log_text.pack(fill="both", expand=True)
            
            progress_window.update()
            
            # Redirigir logs a la ventana
            handler = TextHandler(log_text)
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            logging.getLogger().addHandler(handler)
            
            processor = JofegIDPProcessor()
            processor.process_all()
            
            logging.getLogger().removeHandler(handler)
            progress_window.destroy()
            
            # Verificar si hay errores y ofrecer análisis
            self._check_and_offer_analysis()
            
        except Exception as e:
            messagebox.showerror("Error de Procesamiento", f"Ocurrió un error:\n\n{str(e)}")
    
    def _check_and_offer_analysis(self):
        """Verifica resultados y notifica al usuario"""
        try:
            if not EXCEL_OUTPUT.exists():
                return
            
            df = pd.read_excel(EXCEL_OUTPUT)
            no_match_count = len(df[df['status'] == 'NO_MATCH'])
            ok_count = len(df[df['status'] == 'OK'])
            
            if no_match_count > 0:
                # Generación AUTOMÁTICA del reporte para evitar preguntas
                try:
                    from generate_nomatch_report import analyze_nomatch_errors
                    report_file = analyze_nomatch_errors()
                    report_msg = f"\n\n📄 Se ha generado automáticmente un reporte de errores:\n{Path(report_file).name}"
                except Exception as e:
                    report_msg = f"\n\n❌ No se pudo generar el reporte: {e}"

                messagebox.showinfo(
                    "Procesamiento Finalizado con Advertencias",
                    f"✅ Procesados Correctamente: {ok_count}\n"
                    f"⚠️ Sin Match (Requieren Revisión): {no_match_count}"
                    f"{report_msg}"
                )
            else:
                messagebox.showinfo(
                    "Procesamiento Finalizado",
                    f"✅ Proceso completado exitosamente.\n\n"
                    f"Facturas procesadas: {ok_count}\n"
                    f"Todas las facturas tienen proveedor asignado."
                )
        except Exception as e:
            messagebox.showinfo(
                "Proceso Finalizado",
                f"✅ Procesamiento completado.\n\nRevisa el archivo Excel:\n{EXCEL_OUTPUT}"
            )

    def _generate_smart_report(self):
        """Genera el reporte inteligente (Manual trigger)"""
        try:
            from generate_nomatch_report import analyze_nomatch_errors
            
            # Crear ventana de progreso
            progress = tk.Toplevel(self.root)
            progress.title("Generando Reporte...")
            progress.geometry("400x100")
            tk.Label(progress, text="⏳ Analizando errores...", font=("Arial", 10)).pack(pady=30)
            progress.update()
            
            report_file = analyze_nomatch_errors()
            progress.destroy()
            
            if report_file:
                # Abrir el archivo
                os.startfile(report_file)
                
                messagebox.showinfo(
                    "Reporte Generado",
                    f"📊 Reporte generado correctamente:\n\n{report_file}\n\n"
                    f"El archivo se ha abierto automáticamente.\n"
                    f"Revisa la pestaña 'Resumen y Recomendaciones'."
                )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte:\n{e}")
    
    def verify_last_run(self):
        """Verifica y muestra resumen de la última ejecución"""
        if not EXCEL_OUTPUT.exists():
            messagebox.showinfo(
                "Sin Datos",
                "No se ha ejecutado ningún procesamiento todavía.\n\nEjecuta primero 'Procesamiento de Facturas'."
            )
            return
        
        try:
            df = pd.read_excel(EXCEL_OUTPUT)
            
            # Calcular estadísticas
            total = len(df)
            ok_count = len(df[df['status'] == 'OK'])
            no_match_count = len(df[df['status'] == 'NO_MATCH'])
            error_count = len(df[df['status'] == 'ERROR'])
            
            # Obtener fecha de última modificación
            import datetime
            last_modified = datetime.datetime.fromtimestamp(EXCEL_OUTPUT.stat().st_mtime)
            
            # Ventana de resumen
            summary_window = tk.Toplevel(self.root)
            summary_window.title("Verificación - Última Ejecución")
            summary_window.geometry("500x400")
            summary_window.configure(padx=20, pady=20)
            
            tk.Label(
                summary_window,
                text="📊 Resumen de Última Ejecución",
                font=("Arial", 14, "bold")
            ).pack(pady=(0, 20))
            
            info_frame = tk.Frame(summary_window)
            info_frame.pack(fill="both", expand=True)
            
            info_text = f"""
Última ejecución: {last_modified.strftime('%d/%m/%Y %H:%M:%S')}

ESTADÍSTICAS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total de facturas:        {total}
  ✅ Procesadas OK:          {ok_count} ({ok_count/total*100:.1f}%)
  ⚠️  Sin match (NO_MATCH):   {no_match_count} ({no_match_count/total*100:.1f}%)
  ❌ Errores:                {error_count} ({error_count/total*100:.1f}%)

ARCHIVO:
  {EXCEL_OUTPUT}
            """
            
            text_widget = tk.Text(
                info_frame,
                width=55,
                height=15,
                font=("Consolas", 10),
                wrap=tk.WORD,
                bg="#f8f9fa"
            )
            text_widget.pack(fill="both", expand=True)
            text_widget.insert("1.0", info_text)
            text_widget.config(state=tk.DISABLED)
            
            # Botones de acción
            btn_frame = tk.Frame(summary_window)
            btn_frame.pack(fill="x", pady=(10, 0))
            
            if no_match_count > 0:
                tk.Button(
                    btn_frame,
                    text="📊 Generar Reporte Detallado",
                    command=lambda: [summary_window.destroy(), self._generate_smart_report()],
                    bg="#007bff",
                    fg="white",
                    font=("Arial", 9, "bold"),
                    cursor="hand2"
                ).pack(side="left", padx=5)
                
                tk.Button(
                    btn_frame,
                    text="⚠️ Entrenar desde Errores",
                    command=lambda: [summary_window.destroy(), self.train_from_errors()],
                    bg="#fd7e14",
                    fg="white",
                    font=("Arial", 9, "bold"),
                    cursor="hand2"
                ).pack(side="left", padx=5)
            
            tk.Button(
                btn_frame,
                text="📁 Abrir Excel",
                command=lambda: os.startfile(EXCEL_OUTPUT),
                bg="#28a745",
                fg="white",
                font=("Arial", 9, "bold"),
                cursor="hand2"
            ).pack(side="right", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer los datos:\n{e}")
    
    def train_from_errors(self):
        """Permite entrenar plantillas directamente desde facturas con error"""
        if not EXCEL_OUTPUT.exists():
            messagebox.showinfo(
                "Sin Datos",
                "No se ha ejecutado ningún procesamiento todavía."
            )
            return
        
        try:
            df = pd.read_excel(EXCEL_OUTPUT)
            no_match = df[df['status'] == 'NO_MATCH'].copy()
            
            if len(no_match) == 0:
                messagebox.showinfo(
                    "Sin Errores",
                    "✅ No hay facturas con errores de matching.\n\nTodas las facturas fueron procesadas correctamente."
                )
                return
            
            # Rellenar valores nulos para evitar errores "nan"
            no_match['supplier_tax_id'] = no_match['supplier_tax_id'].fillna("DESCONOCIDO")
            
            # Agrupar por CIF y contar
            cif_counts = no_match['supplier_tax_id'].value_counts()
            
            # Ventana de selección
            select_window = tk.Toplevel(self.root)
            select_window.title("Entrenar desde Errores")
            select_window.geometry("700x500")
            select_window.configure(padx=20, pady=20)
            
            tk.Label(
                select_window,
                text=f"⚠️ Facturas sin Match: {len(no_match)}",
                font=("Arial", 14, "bold")
            ).pack(pady=(0, 10))
            
            tk.Label(
                select_window,
                text="Selecciona una factura para entrenar su plantilla:",
                font=("Arial", 10)
            ).pack(pady=(0, 10))
            
            # Frame con lista y scrollbar
            list_frame = tk.Frame(select_window)
            list_frame.pack(fill="both", expand=True, pady=10)
            
            scrollbar = Scrollbar(list_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = Listbox(
                list_frame,
                font=("Consolas", 9),
                yscrollcommand=scrollbar.set,
                height=20
            )
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Ordenar por frecuencia de CIF (más frecuentes primero)
            no_match['freq'] = no_match['supplier_tax_id'].map(cif_counts)
            no_match = no_match.sort_values('freq', ascending=False)
            
            # Llenar lista
            file_paths = []
            for idx, row in no_match.iterrows():
                cif = row['supplier_tax_id']
                freq = cif_counts[cif]
                filename = row['file_name']
                
                display = f"[{freq:2d}x] {cif:15s} → {filename}"
                listbox.insert(tk.END, display)
                file_paths.append(row['file_path'])
            
            def open_trainer():
                selection = listbox.curselection()
                if not selection:
                    messagebox.showwarning("Sin Selección", "Por favor, selecciona una factura.")
                    return
                
                pdf_path = file_paths[selection[0]]
                if not Path(pdf_path).exists():
                    messagebox.showerror("Error", f"El archivo no existe:\n{pdf_path}")
                    return
                
                select_window.destroy()
                
                # Abrir trainer GUI con el archivo seleccionado
                try:
                    subprocess.Popen(
                        [sys.executable, "jofeg_trainer_gui.py", pdf_path],
                        cwd=BASE_DIR
                    )
                    messagebox.showinfo(
                        "Entrenador Abierto",
                        f"Se ha abierto el entrenador con la factura seleccionada.\n\n"
                        f"Recuerda guardar la plantilla antes de cerrar."
                    )
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir el entrenador:\n{e}")
            
            # Botones
            btn_frame = tk.Frame(select_window)
            btn_frame.pack(fill="x", pady=(10, 0))
            
            tk.Button(
                btn_frame,
                text="📝 Entrenar Seleccionada",
                command=open_trainer,
                bg="#007bff",
                fg="white",
                font=("Arial", 10, "bold"),
                cursor="hand2"
            ).pack(side="left", padx=5)
            
            tk.Button(
                btn_frame,
                text="❌ Cancelar",
                command=select_window.destroy,
                bg="#6c757d",
                fg="white",
                font=("Arial", 10, "bold"),
                cursor="hand2"
            ).pack(side="right", padx=5)
            
            # Doble clic para abrir
            listbox.bind("<Double-Button-1>", lambda e: open_trainer())
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar los errores:\n{e}")
    
    def train_template(self):
        """Lanza el entrenador de plantillas"""
        if not INPUT_DIR.exists():
            messagebox.showwarning(
                "Directorio No Accesible",
                f"El directorio {INPUT_DIR} no es accesible.\n\nVerifica la conexión de red."
            )
            return
        
        try:
            subprocess.Popen([sys.executable, "jofeg_trainer_gui.py"], cwd=BASE_DIR)
            messagebox.showinfo(
                "Entrenador Iniciado",
                "Se ha abierto el Entrenador de Plantillas en una ventana separada."
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el entrenador:\n{e}")
    
    def manage_templates(self):
        """Muestra las plantillas registradas"""
        if not TEMPLATES_PATH.exists():
            messagebox.showinfo(
                "Sin Plantillas",
                "No hay plantillas registradas todavía.\n\nUtiliza 'Entrenar Nuevo Proveedor' para crear la primera."
            )
            return
        
        try:
            with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            
            # Ventana de visualización
            templates_window = tk.Toplevel(self.root)
            templates_window.title("Plantillas Registradas")
            templates_window.geometry("700x400")
            templates_window.configure(padx=20, pady=20)
            
            tk.Label(
                templates_window,
                text=f"📋 Plantillas Registradas: {len(templates)}",
                font=("Arial", 12, "bold")
            ).pack(pady=(0, 10))
            
            text_widget = scrolledtext.ScrolledText(
                templates_window,
                width=80,
                height=20,
                font=("Consolas", 9),
                wrap=tk.WORD
            )
            text_widget.pack(fill="both", expand=True)
            
            for cif, data in templates.items():
                fields = ", ".join(data.get("fields", {}).keys())
                text_widget.insert(tk.END, f"CIF: {cif}\n")
                text_widget.insert(tk.END, f"  Campos configurados: {fields}\n")
                text_widget.insert(tk.END, f"  Número de bloques: {len(data.get('fields', {}))}\n")
                text_widget.insert(tk.END, "-" * 70 + "\n\n")
            
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer las plantillas:\n{e}")
    
    def view_logs(self):
        """Muestra el log de operaciones"""
        if not LOG_FILE.exists():
            messagebox.showinfo(
                "Sin Logs",
                "No se ha generado ningún log todavía.\n\nEjecuta el procesamiento primero."
            )
            return
        
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Ventana de visualización
            log_window = tk.Toplevel(self.root)
            log_window.title("Log de Operaciones")
            log_window.geometry("900x500")
            log_window.configure(padx=20, pady=20)
            
            tk.Label(
                log_window,
                text="📄 Últimas 50 entradas del log",
                font=("Arial", 12, "bold")
            ).pack(pady=(0, 10))
            
            text_widget = scrolledtext.ScrolledText(
                log_window,
                width=100,
                height=25,
                font=("Consolas", 9),
                bg="#1e1e1e",
                fg="#00ff00"
            )
            text_widget.pack(fill="both", expand=True)
            
            for line in lines[-50:]:
                text_widget.insert(tk.END, line)
            
            text_widget.config(state=tk.DISABLED)
            text_widget.see(tk.END)  # Scroll al final
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el log:\n{e}")
    
    def exit_app(self):
        """Cierra la aplicación"""
        if messagebox.askyesno("Confirmar Salida", "¿Desea salir del sistema?"):
            self.root.destroy()


class TextHandler(logging.Handler):
    """Handler para redirigir logs a un widget de texto"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)
        self.text_widget.update()


if __name__ == "__main__":
    root = tk.Tk()
    app = JofegIDPMenuGUI(root)
    root.mainloop()
