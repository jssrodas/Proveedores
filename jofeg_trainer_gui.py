
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from jofeg_trainer import JofegTrainer
import os
from pathlib import Path

class JofegTrainerGUI:
    def __init__(self, root, initial_pdf=None, initial_cif=None):
        self.root = root
        self.root.title("Jofeg IDP - Entrenador Zonal")
        self.root.geometry("500x550")
        self.root.configure(padx=20, pady=20)
        
        self.trainer = JofegTrainer()
        self.current_mapping = None
        self.pdf_path = None

        self._build_ui()
        
        # Pre-rellenar CIF si se proporciona
        if initial_cif:
            self.entries["cif"].insert(0, initial_cif)
            self._update_norm_preview()

        # Si se proporciona un PDF inicial, cargarlo automáticamente
        if initial_pdf and os.path.exists(initial_pdf):
            self.root.after(100, lambda: self._load_pdf(initial_pdf))

    def _build_ui(self):
        # Selección de Archivo
        header = tk.Label(self.root, text="Entrenador de Plantillas Zonal", font=("Arial", 14, "bold"))
        header.pack(pady=(0, 20))

        btn_select = tk.Button(self.root, text="1. Seleccionar Factura PDF", command=self.select_pdf, bg="#0078D4", fg="white", font=("Arial", 10, "bold"), height=2)
        btn_select.pack(fill="x", pady=5)

        self.lbl_file = tk.Label(self.root, text="Archivo: Ninguno", fg="gray", wraplength=450)
        self.lbl_file.pack(pady=5)

        # Formulario de IDs
        frame_id = tk.LabelFrame(self.root, text=" Asignación de IDs (ver mapa PDF) ", padx=10, pady=10)
        frame_id.pack(fill="both", expand=True, pady=10)

        self.fields = {
            "cif": "✏️ Escribe el CIF (Obligatorio):", # Este es manual
            "supplier_tax_id": "ID Bloque donde está el CIF (Opcional):",
            "invoice_number": "ID Bloque Factura Nº:",
            "invoice_date": "ID Bloque Fecha:",
            "base_imponible": "ID Bloque Base Imponible:",
            "iva_importe": "ID Bloque IVA:",
            "total_amount": "ID Bloque Total:"
        }
        self.entries = {}

        for i, (key, label_text) in enumerate(self.fields.items()):
            lbl = tk.Label(frame_id, text=label_text)
            lbl.grid(row=i, column=0, sticky="w", pady=5)
            
            entry = tk.Entry(frame_id)
            entry.grid(row=i, column=1, sticky="ew", padx=(10, 0), pady=5)
            self.entries[key] = entry
            
            if key == "cif":
                self.lbl_norm_cif = tk.Label(frame_id, text="Normalizado: -", fg="blue", font=("Arial", 8, "italic"))
                self.lbl_norm_cif.grid(row=i+1, column=1, sticky="w")
                entry.bind("<KeyRelease>", self._update_norm_preview)
        
        frame_id.columnconfigure(1, weight=1)

        # Botón Guardar
        self.btn_save = tk.Button(self.root, text="2. Guardar Plantilla", command=self.save_template, state="disabled", bg="#28a745", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_save.pack(fill="x", pady=10)

    def _update_norm_preview(self, event=None):
        cif = self.entries["cif"].get().strip()
        from jofeg_idp_processor import JofegIDPProcessor
        norm = JofegIDPProcessor.normalize_id(cif)
        self.lbl_norm_cif.config(text=f"Normalizado: {norm}")

    def select_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Factura PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self._load_pdf(file_path)
    
    def _load_pdf(self, file_path):
        """Carga un PDF (usado tanto por selección manual como automática)"""
        self.pdf_path = file_path
        self.lbl_file.config(text=f"Archivo: {os.path.basename(file_path)}", fg="black")
        
        # Generar mapa y abrir PDF
        try:
            self.current_mapping = self.trainer.generate_mapping_image(file_path)
            self.btn_save.config(state="normal")
            # FEEDBACK NO INTRUSIVO
            self.lbl_file.config(text=f"Archivo: {os.path.basename(file_path)} (MAPA ABIERTO)", fg="green")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar el PDF: {e}")

    def save_template(self):
        cif = self.entries["cif"].get().strip()
        if not cif:
            messagebox.showwarning("Faltan datos", "El CIF es obligatorio para identificar al proveedor.")
            return

        selections = {}
        for key, entry in self.entries.items():
            if key == "cif": continue
            val = entry.get().strip()
            if val.isdigit():
                selections[key] = int(val)
        
        if not selections:
            # Si solo hay CIF, permitimos guardar igualmente para vinculación de proveedor
            confirm = messagebox.askyesno(
                "Mapeo Vacío", 
                "No has mapeado ningún campo (Nº Factura, IVA, etc.).\n\n"
                "¿Deseas guardar la plantilla solo para identificar al proveedor por este CIF?"
            )
            if not confirm:
                return

        try:
            self.trainer.save_template(cif, self.current_mapping, selections)
            messagebox.showinfo(
                "Plantilla Guardada", 
                f"✅ La plantilla para el CIF {cif} se ha guardado correctamente.\n\n"
                "Ahora puedes cerrar esta ventana y volver a procesar las facturas."
            )
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la plantilla: {e}")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    
    # Permitir pasar un PDF y un CIF como argumentos de línea de comandos
    initial_pdf = sys.argv[1] if len(sys.argv) > 1 else None
    initial_cif = sys.argv[2] if len(sys.argv) > 2 else None
    app = JofegTrainerGUI(root, initial_pdf, initial_cif)
    root.mainloop()
