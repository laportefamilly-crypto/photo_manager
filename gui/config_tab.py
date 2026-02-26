"""Onglet Configuration — dark SaaS."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import gui.theme as th


class ConfigTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(style="TFrame")
        self._build()

    def _build(self):
        # Zone scrollable
        canvas = tk.Canvas(self, bg=th.BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=th.BG)
        win = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        # ── Titre de page ─────────────────────────────────────────────────────
        title_row = tk.Frame(inner, bg=th.BG)
        title_row.pack(fill=tk.X, padx=32, pady=(28, 20))
        tk.Label(title_row, text="Configuration",
                 bg=th.BG, fg=th.TEXT, font=th.F_TITLE).pack(side=tk.LEFT)
        th.badge(title_row, "Étape 1", th.PURPLE, th.BG).pack(side=tk.LEFT, padx=12)

        # ── Card : Dossiers source ────────────────────────────────────────────
        src_card = th.card(inner)
        src_card.pack(fill=tk.X, padx=32, pady=(0, 16))
        self._card_header(src_card, "Dossiers source", "Photos à analyser")

        list_frame = tk.Frame(src_card, bg=th.SURFACE)
        list_frame.pack(fill=tk.X, padx=20, pady=(0, 4))

        self.src_listbox = tk.Listbox(
            list_frame, height=4,
            selectmode=tk.EXTENDED,
            font=th.F_MONO,
            bg=th.SURFACE2, fg=th.TEXT,
            relief="flat", bd=0,
            selectbackground=th._blend(th.PURPLE, th.SURFACE2, 0.25),
            selectforeground=th.PURPLE,
            activestyle="none",
            highlightthickness=1,
            highlightbackground=th.BORDER,
            highlightcolor=th.PURPLE,
        )
        self.src_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrolly = ttk.Scrollbar(list_frame, command=self.src_listbox.yview)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        self.src_listbox.configure(yscrollcommand=scrolly.set)

        btn_row = tk.Frame(src_card, bg=th.SURFACE)
        btn_row.pack(fill=tk.X, padx=20, pady=(8, 16))
        ttk.Button(btn_row, text="+ Ajouter",
                   style="Primary.TButton", command=self._add_source).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Retirer",
                   style="Ghost.TButton", command=self._remove_source).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Effacer tout",
                   style="Ghost.TButton", command=self._clear_sources).pack(side=tk.LEFT)

        # ── Card : Destination ────────────────────────────────────────────────
        dest_card = th.card(inner)
        dest_card.pack(fill=tk.X, padx=32, pady=(0, 16))
        self._card_header(dest_card, "Dossier destination", "Où seront copiées les photos organisées")

        dest_row = tk.Frame(dest_card, bg=th.SURFACE)
        dest_row.pack(fill=tk.X, padx=20, pady=(0, 16))

        self.dest_var = tk.StringVar()
        entry_frame = tk.Frame(dest_row, bg=th.SURFACE2,
                               highlightbackground=th.BORDER, highlightthickness=1)
        entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Entry(entry_frame, textvariable=self.dest_var,
                 font=th.F_MONO, bg=th.SURFACE2, fg=th.TEXT,
                 insertbackground=th.PURPLE,
                 relief="flat", bd=6).pack(fill=tk.X)
        ttk.Button(dest_row, text="Parcourir…",
                   command=self._choose_dest).pack(side=tk.LEFT)

        # ── Card : Options ────────────────────────────────────────────────────
        opt_card = th.card(inner)
        opt_card.pack(fill=tk.X, padx=32, pady=(0, 16))
        self._card_header(opt_card, "Options", "Comportement du scan et de l'organisation")

        opt_inner = tk.Frame(opt_card, bg=th.SURFACE)
        opt_inner.pack(fill=tk.X, padx=20, pady=(0, 16))

        ttk.Checkbutton(
            opt_inner,
            text="Déplacer les fichiers (au lieu de copier)",
            variable=self.app.state["move_files"],
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 12))

        tk.Label(opt_inner, text="Seuil similarité visuelle (dhash 0–64) :",
                 bg=th.SURFACE, fg=th.TEXT, font=th.F_BODY).grid(
                 row=1, column=0, sticky=tk.W)
        ttk.Spinbox(opt_inner, from_=0, to=64, increment=1, width=6,
                    textvariable=self.app.state["similarity_threshold"],
                    ).grid(row=1, column=1, sticky=tk.W, padx=10)
        tk.Label(opt_inner, text="(plus bas = plus strict)",
                 bg=th.SURFACE, fg=th.MUTED, font=th.F_SMALL).grid(
                 row=1, column=2, sticky=tk.W)

        # ── Bouton valider ────────────────────────────────────────────────────
        cta = tk.Frame(inner, bg=th.BG)
        cta.pack(fill=tk.X, padx=32, pady=(4, 32))
        ttk.Button(cta, text="Valider  →  Aller au Scan",
                   style="Primary.TButton", command=self._validate).pack(side=tk.RIGHT)

    # ── Helpers internes ──────────────────────────────────────────────────────

    def _card_header(self, card: tk.Frame, title: str, subtitle: str = ""):
        hf = tk.Frame(card, bg=th.SURFACE)
        hf.pack(fill=tk.X, padx=20, pady=(16, 10))
        tk.Label(hf, text=title, bg=th.SURFACE,
                 fg=th.TEXT, font=th.F_HEADING).pack(side=tk.LEFT)
        if subtitle:
            tk.Label(hf, text=f"  —  {subtitle}", bg=th.SURFACE,
                     fg=th.MUTED, font=th.F_SMALL).pack(side=tk.LEFT)
        th.divider(card, bg=th.SURFACE).pack(fill=tk.X, padx=20, pady=(0, 12))

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

    def load_config(self, data: dict):
        self.src_listbox.delete(0, tk.END)
        for p in data.get("source_dirs", []):
            self.src_listbox.insert(tk.END, p)
        self.dest_var.set(data.get("dest_dir", ""))

    def _validate(self):
        sources = list(self.src_listbox.get(0, tk.END))
        dest    = self.dest_var.get().strip()
        if not sources:
            messagebox.showwarning("Configuration", "Ajoutez au moins un dossier source.")
            return
        if not dest:
            messagebox.showwarning("Configuration", "Choisissez un dossier destination.")
            return
        dest_path = Path(dest)
        for sp in [Path(s) for s in sources]:
            if dest_path == sp or dest_path.is_relative_to(sp):
                messagebox.showwarning("Configuration",
                    f"La destination ne peut pas être à l'intérieur d'une source.\n{dest_path}")
                return
        self.app.state["source_dirs"] = [Path(s) for s in sources]
        self.app.state["dest_dir"]    = dest_path
        self.app.set_status(f"{len(sources)} source(s) configurée(s)")
        self.app.switch_to_tab(1)
