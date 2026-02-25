"""Onglet Configuration : dossiers source/destination, options."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class ConfigTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 6}

        # === Dossiers source ===
        src_frame = ttk.LabelFrame(self, text="Dossiers source (photos à traiter)")
        src_frame.pack(fill=tk.X, **pad)

        self.src_listbox = tk.Listbox(src_frame, height=5, selectmode=tk.EXTENDED,
                                      font=("Consolas", 9), bg="white")
        self.src_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        src_scroll = ttk.Scrollbar(src_frame, orient=tk.VERTICAL, command=self.src_listbox.yview)
        src_scroll.pack(side=tk.LEFT, fill=tk.Y, pady=6)
        self.src_listbox.configure(yscrollcommand=src_scroll.set)

        src_btn_frame = ttk.Frame(src_frame)
        src_btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        ttk.Button(src_btn_frame, text="+ Ajouter", command=self._add_source).pack(fill=tk.X, pady=2)
        ttk.Button(src_btn_frame, text="- Retirer", command=self._remove_source).pack(fill=tk.X, pady=2)
        ttk.Button(src_btn_frame, text="Tout effacer", command=self._clear_sources).pack(fill=tk.X, pady=2)

        # === Dossier destination ===
        dest_frame = ttk.LabelFrame(self, text="Dossier destination")
        dest_frame.pack(fill=tk.X, **pad)

        self.dest_var = tk.StringVar(value="")
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, font=("Consolas", 9))
        dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=8)
        ttk.Button(dest_frame, text="Parcourir…", command=self._choose_dest).pack(side=tk.LEFT, padx=6, pady=8)

        # === Options ===
        opt_frame = ttk.LabelFrame(self, text="Options")
        opt_frame.pack(fill=tk.X, **pad)

        ttk.Checkbutton(
            opt_frame,
            text="Déplacer les fichiers (au lieu de copier)",
            variable=self.app.state["move_files"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

        ttk.Label(opt_frame, text="Seuil similarité visuelle (distance dhash, 0–64) :").grid(
            row=1, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Spinbox(
            opt_frame,
            from_=0, to=64, increment=1,
            textvariable=self.app.state["similarity_threshold"],
            width=6,
        ).grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(opt_frame, text="(Plus la valeur est basse, plus les photos doivent être semblables)").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=8, pady=(0, 4))

        # === Bouton validation ===
        validate_frame = ttk.Frame(self)
        validate_frame.pack(fill=tk.X, padx=12, pady=8)
        ttk.Button(
            validate_frame,
            text="✔  Valider et aller vers Scan",
            style="Accent.TButton",
            command=self._validate,
        ).pack(side=tk.RIGHT)

    def load_config(self, data: dict):
        """Peuple les champs depuis un dict de configuration sauvegardé."""
        self.src_listbox.delete(0, tk.END)
        for path in data.get("source_dirs", []):
            self.src_listbox.insert(tk.END, path)
        self.dest_var.set(data.get("dest_dir", ""))

    def _add_source(self):
        folder = filedialog.askdirectory(title="Sélectionner un dossier source")
        if folder and folder not in self.src_listbox.get(0, tk.END):
            self.src_listbox.insert(tk.END, folder)

    def _remove_source(self):
        for idx in reversed(self.src_listbox.curselection()):
            self.src_listbox.delete(idx)

    def _clear_sources(self):
        self.src_listbox.delete(0, tk.END)

    def _choose_dest(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier destination")
        if folder:
            self.dest_var.set(folder)

    def _validate(self):
        sources = list(self.src_listbox.get(0, tk.END))
        dest = self.dest_var.get().strip()

        if not sources:
            messagebox.showwarning("Configuration", "Veuillez ajouter au moins un dossier source.")
            return
        if not dest:
            messagebox.showwarning("Configuration", "Veuillez choisir un dossier destination.")
            return

        dest_path = Path(dest)
        source_paths = [Path(s) for s in sources]

        # Vérification que la destination ne fait pas partie des sources
        for sp in source_paths:
            if dest_path == sp or dest_path.is_relative_to(sp):
                messagebox.showwarning(
                    "Configuration",
                    f"Le dossier destination ne peut pas être à l'intérieur d'un dossier source.\n{dest_path}",
                )
                return

        self.app.state["source_dirs"] = source_paths
        self.app.state["dest_dir"] = dest_path
        self.app.set_status(f"Configuration validée — {len(sources)} source(s), destination : {dest}")
        self.app.switch_to_tab(1)
