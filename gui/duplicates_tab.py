"""Onglet Doublons — dark SaaS."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import gui.theme as th

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

THUMB_SIZE = (130, 100)


class DuplicateGroup(tk.Frame):
    def __init__(self, parent, group: list[Path], group_type: str, index: int):
        super().__init__(parent, bg=th.SURFACE,
                         highlightbackground=th.BORDER, highlightthickness=1)
        self.group      = group
        self.group_type = group_type
        self.check_vars: list[tk.BooleanVar] = []
        self._thumbs    = []
        self._build(index)

    def _build(self, index: int):
        accent = th.PURPLE if self.group_type == "exact" else "#a855f7"
        label  = "Exact  ·  MD5" if self.group_type == "exact" else "Visuel  ·  dhash"

        # En-tête coloré
        hdr = tk.Frame(self, bg=th._blend(accent, th.SURFACE, 0.12))
        hdr.pack(fill=tk.X)

        tk.Label(hdr, text=f"Groupe {index+1}", bg=hdr["bg"],
                 fg=accent, font=("Segoe UI", 9, "bold"),
                 padx=14, pady=6).pack(side=tk.LEFT)
        tk.Label(hdr, text=label, bg=hdr["bg"],
                 fg=th.MUTED, font=th.F_TINY, padx=0).pack(side=tk.LEFT)
        tk.Label(hdr, text=f"{len(self.group)} fichiers", bg=hdr["bg"],
                 fg=th.MUTED, font=th.F_TINY).pack(side=tk.RIGHT, padx=14)

        tk.Button(hdr, text="Sélectionner sauf 1er",
                  bg=hdr["bg"], fg=accent, relief="flat", bd=0,
                  activebackground=hdr["bg"], activeforeground=accent,
                  font=th.F_TINY, cursor="hand2",
                  command=self._select_all_but_first).pack(side=tk.RIGHT, padx=4)

        th.divider(self, bg=th.SURFACE).pack(fill=tk.X)

        # Cartes photos
        cards_row = tk.Frame(self, bg=th.SURFACE)
        cards_row.pack(fill=tk.X, padx=14, pady=12)

        for i, path in enumerate(self.group):
            var = tk.BooleanVar(value=False)
            self.check_vars.append(var)
            self._build_card(cards_row, path, var, i, accent)

    def _build_card(self, parent, path: Path, var: tk.BooleanVar, idx: int, accent: str):
        card = tk.Frame(parent, bg=th.SURFACE2,
                        highlightbackground=th.BORDER, highlightthickness=1)
        card.pack(side=tk.LEFT, padx=6)

        # Miniature
        if PIL_AVAILABLE and path.exists():
            try:
                img = Image.open(path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._thumbs.append(photo)
                tk.Label(card, image=photo, bg=th.SURFACE2).pack(padx=8, pady=8)
            except Exception:
                self._placeholder(card)
        else:
            self._placeholder(card)

        th.divider(card, bg=th.SURFACE2).pack(fill=tk.X, padx=6)

        # Nom du fichier
        try:
            size_kb = path.stat().st_size // 1024
            info = f"{path.name}\n{size_kb} Ko"
        except Exception:
            info = path.name
        tk.Label(card, text=info, bg=th.SURFACE2, fg=th.MUTED,
                 font=th.F_MONO_SM, wraplength=148,
                 justify=tk.CENTER).pack(padx=6, pady=(6, 0))

        # Badge "Conserver" sur le premier
        if idx == 0:
            badge_bg = th._blend(th.GREEN, th.SURFACE2, 0.15)
            tk.Label(card, text="● Conserver", bg=badge_bg, fg=th.GREEN,
                     font=th.F_TINY, padx=8, pady=2).pack(pady=(4, 0))

        ttk.Checkbutton(card, text="Supprimer", variable=var).pack(pady=6)

    def _placeholder(self, card):
        tk.Label(card, text="Aperçu\nindisponible",
                 bg=th.SURFACE2, fg=th.MUTED, font=th.F_SMALL,
                 width=16, height=6).pack(padx=8, pady=8)

    def _select_all_but_first(self):
        for i, v in enumerate(self.check_vars):
            v.set(i != 0)

    def get_selected_paths(self) -> list[Path]:
        return [p for p, v in zip(self.group, self.check_vars) if v.get()]


class DuplicatesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(style="TFrame")
        self._group_widgets: list[DuplicateGroup] = []
        self._exact_groups:  list[list[Path]] = []
        self._visual_groups: list[list[Path]] = []
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=th.SURFACE,
                           highlightbackground=th.BORDER, highlightthickness=1)
        toolbar.grid(row=0, column=0, sticky="ew")

        tb_inner = tk.Frame(toolbar, bg=th.SURFACE)
        tb_inner.pack(fill=tk.X, padx=20, pady=12)

        self.label_summary = tk.Label(tb_inner, text="Aucun doublon détecté.",
                                      bg=th.SURFACE, fg=th.MUTED, font=th.F_BODY)
        self.label_summary.pack(side=tk.LEFT)

        self.btn_delete = ttk.Button(tb_inner, text="Supprimer la sélection",
                                     style="Danger.TButton",
                                     command=self._delete_selected, state=tk.DISABLED)
        self.btn_delete.pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(tb_inner, text="Désélectionner tout",
                   style="Ghost.TButton", command=self._deselect_all).pack(side=tk.RIGHT)

        # ── Filtres ───────────────────────────────────────────────────────────
        filter_bar = tk.Frame(self, bg=th.BG)
        filter_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 4))

        tk.Label(filter_bar, text="Afficher :", bg=th.BG,
                 fg=th.MUTED, font=th.F_SMALL).pack(side=tk.LEFT, padx=(0, 8))
        self.filter_var = tk.StringVar(value="all")
        for val, label in (("all", "Tous"), ("exact", "Exacts"), ("visual", "Visuels")):
            ttk.Radiobutton(filter_bar, text=label, variable=self.filter_var,
                            value=val, command=self._apply_filter).pack(side=tk.LEFT, padx=4)

        # ── Zone scrollable ───────────────────────────────────────────────────
        container = tk.Frame(self, bg=th.BG)
        container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(4, 16))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, bg=th.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.grid(row=0, column=0, sticky="nsew")

        self.scroll_frame = tk.Frame(canvas, bg=th.BG)
        self.scroll_win   = canvas.create_window((0, 0), window=self.scroll_frame, anchor=tk.NW)
        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self.scroll_win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    # ── Public ────────────────────────────────────────────────────────────────

    def on_duplicates_found(self, exact, visual):
        self._exact_groups  = exact
        self._visual_groups = visual
        self._render_groups()

    def _render_groups(self):
        for w in self._group_widgets: w.destroy()
        self._group_widgets.clear()

        flt = self.filter_var.get()
        groups = []
        if flt in ("all", "exact"):  groups += [("exact",  g) for g in self._exact_groups]
        if flt in ("all", "visual"): groups += [("visual", g) for g in self._visual_groups]

        total = len(self._exact_groups) + len(self._visual_groups)
        self.label_summary.config(text=(
            f"{len(self._exact_groups)} groupe(s) exact(s)  ·  "
            f"{len(self._visual_groups)} groupe(s) visuel(s)"
            if total else "Aucun doublon détecté."))

        for idx, (gtype, group) in enumerate(groups):
            w = DuplicateGroup(self.scroll_frame, group, gtype, idx)
            w.pack(fill=tk.X, pady=(0, 10))
            self._group_widgets.append(w)

        self.btn_delete.config(state=tk.NORMAL if groups else tk.DISABLED)

    def _apply_filter(self): self._render_groups()

    def _deselect_all(self):
        for w in self._group_widgets:
            for v in w.check_vars: v.set(False)

    def _delete_selected(self):
        to_delete = [p for w in self._group_widgets for p in w.get_selected_paths()]
        if not to_delete:
            messagebox.showinfo("Aucune sélection", "Aucun fichier sélectionné.")
            return
        if not messagebox.askyesno("Confirmer",
            f"{len(to_delete)} fichier(s) → _corbeille.\nCette action est réversible.\nConfirmer ?"):
            return
        dest = self.app.state["dest_dir"]
        if not dest:
            messagebox.showerror("Erreur", "Aucun dossier destination configuré.")
            return
        threading.Thread(target=self._run_trash,
                         args=(to_delete, Path(dest) / "_corbeille"), daemon=True).start()

    def _run_trash(self, paths, trash_dir):
        from core.duplicate_finder import move_to_trash
        moved, errors = move_to_trash(paths, trash_dir)
        self.app.queue.put({"kind": "trash_done", "moved": moved,
                            "original_paths": paths, "errors": errors})
        self.app.queue.put({"kind": "log",
                            "text": f"Corbeille : {len(moved)} fichier(s) déplacés, {len(errors)} erreur(s).",
                            "level": "success" if not errors else "warning"})
        self.app.after(0, self._refresh_after_trash, paths)

    def _refresh_after_trash(self, deleted_paths):
        deleted = set(deleted_paths)
        for attr in ("_exact_groups", "_visual_groups"):
            setattr(self, attr, [
                [p for p in g if p not in deleted]
                for g in getattr(self, attr)
                if sum(1 for p in g if p not in deleted) > 1
            ])
        self._render_groups()
