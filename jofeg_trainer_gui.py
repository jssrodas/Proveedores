
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from jofeg_trainer import JofegTrainer
import os
from pathlib import Path

class JofegTrainerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Jofeg IDP - Entrenador Zonal")
        self.root.geometry("500x550")
        self.root.configure(padx=20, pady=20)
        
        self.trainer = JofegTrainer()
        self.current_mapping = None
        self.pdf_path = None

        self._build_ui()

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
            "cif": "CIF del Proveedor:",
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
        
        frame_id.columnconfigure(1, weight=1)

        # Botón Guardar
        self.btn_save = tk.Button(self.root, text="2. Guardar Plantilla", command=self.save_template, state="disabled", bg="#28a745", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_save.pack(fill="x", pady=10)

    def select_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Factura PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self.pdf_path = file_path
            self.lbl_file.config(text=f"Archivo: {os.path.basename(file_path)}", fg="black")
            
            # Generar mapa y abrir PDF
            try:
                self.current_mapping = self.trainer.generate_mapping_image(file_path)
                self.btn_save.config(state="normal")
                messagebox.showinfo("Mapa Generado", "Se ha abierto el PDF con los números rojos.\nIdentifica los IDs y rellena el formulario.")
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
            messagebox.showwarning("Faltan IDs", "Debes introducir al menos un ID de bloque.")
            return

        try:
            self.trainer.save_template(cif, self.current_mapping, selections)
            messagebox.showinfo("Éxito", f"Plantilla guardada correctamente para {cif}")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la plantilla: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = JofegTrainerGUI(root)
    root.mainloop()
