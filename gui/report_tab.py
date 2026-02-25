"""Onglet Rapport : statistiques et export."""
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class ReportTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        pad = {"padx": 16, "pady": 8}

        title = ttk.Label(self, text="Rapport de session", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=tk.W, **pad)

        # Grille de stats
        stats_frame = ttk.LabelFrame(self, text="Statistiques")
        stats_frame.pack(fill=tk.X, **pad)

        labels = [
            ("Photos trouvées lors du scan :", "photos_count"),
            ("Photos organisées (copiées/déplacées) :", "organized_count"),
            ("Groupes de doublons exacts :", "exact_groups"),
            ("Groupes de doublons visuels :", "visual_groups"),
            ("Fichiers mis en corbeille :", "trash_count"),
            ("Erreurs :", "error_count"),
        ]

        self._stat_vars: dict[str, tk.StringVar] = {}
        for row, (text, key) in enumerate(labels):
            ttk.Label(stats_frame, text=text).grid(row=row, column=0, sticky=tk.W, padx=12, pady=3)
            var = tk.StringVar(value="—")
            self._stat_vars[key] = var
            ttk.Label(stats_frame, textvariable=var, font=("Segoe UI", 10, "bold")).grid(
                row=row, column=1, sticky=tk.W, padx=12, pady=3
            )

        # Erreurs détaillées
        err_frame = ttk.LabelFrame(self, text="Erreurs détaillées")
        err_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.err_text = tk.Text(
            err_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), height=8, bg="#fff8f8",
        )
        self.err_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        err_scroll = ttk.Scrollbar(err_frame, command=self.err_text.yview)
        err_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.err_text.configure(yscrollcommand=err_scroll.set)

        # Boutons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, **pad)

        ttk.Button(btn_frame, text="🔄  Actualiser", command=self.refresh).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="💾  Exporter le rapport (TXT)", command=self._export).pack(side=tk.RIGHT, padx=4)

    def refresh(self):
        s = self.app.state
        self._stat_vars["photos_count"].set(str(len(s["photos"])))
        self._stat_vars["organized_count"].set(str(len(s["organized"])))
        self._stat_vars["exact_groups"].set(str(len(s["exact_duplicates"])))
        self._stat_vars["visual_groups"].set(str(len(s["visual_duplicates"])))
        self._stat_vars["trash_count"].set(str(len(s["trash_moved"])))
        self._stat_vars["error_count"].set(str(len(s["errors"])))

        # Mise à jour des erreurs
        self.err_text.config(state=tk.NORMAL)
        self.err_text.delete("1.0", tk.END)
        if s["errors"]:
            for path, msg in s["errors"]:
                path_str = str(path) if path else "Inconnu"
                self.err_text.insert(tk.END, f"• {path_str}\n  → {msg}\n\n")
        else:
            self.err_text.insert(tk.END, "Aucune erreur.")
        self.err_text.config(state=tk.DISABLED)

    def _export(self):
        dest = filedialog.asksaveasfilename(
            title="Enregistrer le rapport",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")],
            initialfile=f"rapport_photo_manager_{datetime.now():%Y%m%d_%H%M%S}.txt",
        )
        if not dest:
            return

        s = self.app.state
        lines = [
            "=" * 60,
            "RAPPORT PHOTO MANAGER",
            f"Date : {datetime.now():%d/%m/%Y %H:%M:%S}",
            "=" * 60,
            "",
            "STATISTIQUES",
            "-" * 40,
            f"Photos trouvées         : {len(s['photos'])}",
            f"Photos organisées       : {len(s['organized'])}",
            f"Groupes doublons exacts : {len(s['exact_duplicates'])}",
            f"Groupes doublons visuels: {len(s['visual_duplicates'])}",
            f"Fichiers en corbeille   : {len(s['trash_moved'])}",
            f"Erreurs                 : {len(s['errors'])}",
            "",
        ]

        if s["source_dirs"]:
            lines += ["DOSSIERS SOURCE", "-" * 40]
            lines += [f"  {d}" for d in s["source_dirs"]]
            lines.append("")

        if s["dest_dir"]:
            lines += [f"DESTINATION : {s['dest_dir']}", ""]

        if s["errors"]:
            lines += ["ERREURS", "-" * 40]
            for path, msg in s["errors"]:
                lines.append(f"  {path} → {msg}")
            lines.append("")

        if s["trash_moved"]:
            lines += ["FICHIERS MIS EN CORBEILLE", "-" * 40]
            lines += [f"  {p}" for p in s["trash_moved"]]
            lines.append("")

        lines += ["=" * 60, "Fin du rapport"]

        try:
            Path(dest).write_text("\n".join(lines), encoding="utf-8")
            messagebox.showinfo("Export", f"Rapport enregistré :\n{dest}")
        except OSError as e:
            messagebox.showerror("Erreur", f"Impossible d'écrire le fichier :\n{e}")
