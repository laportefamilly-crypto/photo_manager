"""Onglet Rapport — dark SaaS, métriques style dashboard analytics."""
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import gui.theme as th


class ReportTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(style="TFrame")
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Titre ─────────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=th.BG)
        title_bar.grid(row=0, column=0, sticky="ew", padx=32, pady=(24, 0))

        tk.Label(title_bar, text="Rapport de session",
                 bg=th.BG, fg=th.TEXT, font=th.F_TITLE).pack(side=tk.LEFT)

        ttk.Button(title_bar, text="Exporter TXT",
                   style="Primary.TButton", command=self._export).pack(side=tk.RIGHT)
        ttk.Button(title_bar, text="Actualiser",
                   style="Ghost.TButton", command=self.refresh).pack(side=tk.RIGHT, padx=(0, 8))

        # ── Grille de métriques (style dashboard analytics) ───────────────────
        metrics_row = tk.Frame(self, bg=th.BG)
        metrics_row.grid(row=1, column=0, sticky="ew", padx=32, pady=20)

        METRICS = [
            ("photos_count",    "Photos",           th.PURPLE),
            ("organized_count", "Organisées",        th.GREEN),
            ("exact_groups",    "Doublons exacts",   th.ORANGE),
            ("visual_groups",   "Doublons visuels",  "#a855f7"),
            ("trash_count",     "En corbeille",      th.PINK),
            ("error_count",     "Erreurs",           th.PINK),
        ]

        self._stat_vars: dict[str, tk.StringVar] = {}

        for col, (key, label, color) in enumerate(METRICS):
            cell = tk.Frame(metrics_row, bg=th.SURFACE,
                            highlightbackground=th.BORDER, highlightthickness=1)
            cell.grid(row=0, column=col, padx=(0, 10), sticky="nsew")
            metrics_row.columnconfigure(col, weight=1)

            inner = tk.Frame(cell, bg=th.SURFACE)
            inner.pack(padx=16, pady=14)

            var = tk.StringVar(value="—")
            self._stat_vars[key] = var

            # Grand chiffre coloré
            tk.Label(inner, textvariable=var, bg=th.SURFACE,
                     fg=color, font=th.F_DISPLAY).pack()

            # Libellé + barre colorée
            lbl_row = tk.Frame(inner, bg=th.SURFACE)
            lbl_row.pack(fill=tk.X, pady=(4, 0))
            tk.Frame(lbl_row, bg=color, width=3, height=12).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(lbl_row, text=label, bg=th.SURFACE,
                     fg=th.MUTED, font=th.F_SMALL).pack(side=tk.LEFT)

        # ── Journal des erreurs ───────────────────────────────────────────────
        err_outer = tk.Frame(self, bg=th.BG)
        err_outer.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 24))
        err_outer.columnconfigure(0, weight=1)
        err_outer.rowconfigure(1, weight=1)

        err_hdr = tk.Frame(err_outer, bg=th.BG)
        err_hdr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Label(err_hdr, text="Erreurs détaillées",
                 bg=th.BG, fg=th.TEXT, font=th.F_HEADING).pack(side=tk.LEFT)

        err_card = th.card(err_outer)
        err_card.grid(row=1, column=0, sticky="nsew")
        err_card.columnconfigure(0, weight=1)
        err_card.rowconfigure(0, weight=1)

        self.err_text = tk.Text(
            err_card, wrap=tk.WORD, state=tk.DISABLED,
            font=th.F_MONO, bg=th.SURFACE, fg=th.MUTED,
            relief="flat", borderwidth=0,
            padx=16, pady=12,
            selectbackground=th._blend(th.PURPLE, th.SURFACE, 0.3),
        )
        self.err_text.grid(row=0, column=0, sticky="nsew")

        err_scroll = ttk.Scrollbar(err_card, command=self.err_text.yview)
        err_scroll.grid(row=0, column=1, sticky="ns")
        self.err_text.configure(yscrollcommand=err_scroll.set)

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self):
        s = self.app.state
        self._stat_vars["photos_count"].set(str(len(s["photos"])))
        self._stat_vars["organized_count"].set(str(len(s["organized"])))
        self._stat_vars["exact_groups"].set(str(len(s["exact_duplicates"])))
        self._stat_vars["visual_groups"].set(str(len(s["visual_duplicates"])))
        self._stat_vars["trash_count"].set(str(len(s["trash_moved"])))
        self._stat_vars["error_count"].set(str(len(s["errors"])))

        self.err_text.config(state=tk.NORMAL)
        self.err_text.delete("1.0", tk.END)
        if s["errors"]:
            for path, msg in s["errors"]:
                self.err_text.insert(tk.END, f"• {path}\n  {msg}\n\n")
        else:
            self.err_text.insert(tk.END, "Aucune erreur.")
        self.err_text.config(state=tk.DISABLED)

    def _export(self):
        dest = filedialog.asksaveasfilename(
            title="Enregistrer le rapport",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt")],
            initialfile=f"rapport_{datetime.now():%Y%m%d_%H%M%S}.txt",
        )
        if not dest:
            return
        s = self.app.state
        lines = [
            "=" * 60, "RAPPORT PHOTO MANAGER",
            f"Date : {datetime.now():%d/%m/%Y %H:%M:%S}", "=" * 60, "",
            "STATISTIQUES", "-" * 40,
            f"Photos trouvees           : {len(s['photos'])}",
            f"Photos organisees         : {len(s['organized'])}",
            f"Doublons exacts (groupes) : {len(s['exact_duplicates'])}",
            f"Doublons visuels (groupes): {len(s['visual_duplicates'])}",
            f"Fichiers en corbeille     : {len(s['trash_moved'])}",
            f"Erreurs                   : {len(s['errors'])}", "",
        ]
        if s["source_dirs"]:
            lines += ["SOURCES", "-"*40] + [f"  {d}" for d in s["source_dirs"]] + [""]
        if s["dest_dir"]:
            lines += [f"DESTINATION : {s['dest_dir']}", ""]
        if s["errors"]:
            lines += ["ERREURS", "-"*40] + [f"  {p} -> {m}" for p,m in s["errors"]] + [""]
        if s["trash_moved"]:
            lines += ["CORBEILLE", "-"*40] + [f"  {p}" for p in s["trash_moved"]] + [""]
        lines += ["="*60, "Fin du rapport"]
        try:
            Path(dest).write_text("\n".join(lines), encoding="utf-8")
            messagebox.showinfo("Export", f"Rapport enregistre :\n{dest}")
        except OSError as e:
            messagebox.showerror("Erreur", str(e))
