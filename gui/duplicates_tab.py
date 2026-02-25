"""Onglet Doublons : affichage des paires, aperçus, sélection et suppression."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

THUMB_SIZE = (120, 90)


class DuplicateGroup(ttk.Frame):
    """Widget représentant un groupe de doublons (ligne dans la liste)."""

    def __init__(self, parent, group: list[Path], group_type: str, index: int):
        super().__init__(parent, relief=tk.GROOVE, borderwidth=1)
        self.group = group
        self.group_type = group_type
        self.index = index
        self.check_vars: list[tk.BooleanVar] = []
        self._thumbs = []  # Keep references to avoid GC
        self._build()

    def _build(self):
        # Étiquette type + groupe
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=4, pady=2)

        type_label = "Exact (MD5)" if self.group_type == "exact" else "Visuel (dhash)"
        ttk.Label(header, text=f"Groupe {self.index + 1} — {type_label} — {len(self.group)} fichiers",
                  font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        ttk.Button(header, text="Tout sélectionner sauf 1er",
                   command=self._select_all_but_first).pack(side=tk.RIGHT, padx=4)

        # Cartes pour chaque photo
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill=tk.X, padx=4, pady=4)

        for i, path in enumerate(self.group):
            var = tk.BooleanVar(value=False)
            self.check_vars.append(var)
            self._build_card(cards_frame, path, var, i)

    def _build_card(self, parent, path: Path, var: tk.BooleanVar, idx: int):
        card = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=1)
        card.pack(side=tk.LEFT, padx=6, pady=4)

        # Miniature
        if PIL_AVAILABLE and path.exists():
            try:
                img = Image.open(path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._thumbs.append(photo)
                lbl_img = ttk.Label(card, image=photo)
                lbl_img.pack(padx=4, pady=4)
            except Exception:
                ttk.Label(card, text="[Aperçu\nindisponible]", width=14, anchor=tk.CENTER).pack(padx=4, pady=4)
        else:
            ttk.Label(card, text="[Aperçu\nindisponible]", width=14, anchor=tk.CENTER).pack(padx=4, pady=4)

        # Nom + taille
        try:
            size_kb = path.stat().st_size // 1024
            info = f"{path.name}\n{size_kb} Ko"
        except Exception:
            info = path.name

        ttk.Label(card, text=info, wraplength=130, justify=tk.CENTER, font=("Segoe UI", 8)).pack(padx=4)

        # Case à cocher
        chk = ttk.Checkbutton(card, text="Supprimer", variable=var)
        chk.pack(pady=4)

        # Mettre en évidence le premier fichier
        if idx == 0:
            ttk.Label(card, text="(conserver)", foreground="green",
                      font=("Segoe UI", 8, "italic")).pack()

    def _select_all_but_first(self):
        for i, var in enumerate(self.check_vars):
            var.set(i != 0)

    def get_selected_paths(self) -> list[Path]:
        return [p for p, v in zip(self.group, self.check_vars) if v.get()]


class DuplicatesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._group_widgets: list[DuplicateGroup] = []
        self._build()

    def _build(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=12, pady=6)

        self.label_summary = ttk.Label(toolbar, text="Aucun doublon détecté pour l'instant.")
        self.label_summary.pack(side=tk.LEFT)

        self.btn_delete = ttk.Button(
            toolbar, text="🗑  Supprimer la sélection (vers _corbeille)",
            command=self._delete_selected, state=tk.DISABLED,
        )
        self.btn_delete.pack(side=tk.RIGHT, padx=4)

        ttk.Button(toolbar, text="Tout désélectionner", command=self._deselect_all).pack(side=tk.RIGHT, padx=4)

        # Filtre
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=12)
        ttk.Label(filter_frame, text="Afficher :").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="Tous", variable=self.filter_var, value="all", command=self._apply_filter).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(filter_frame, text="Exacts", variable=self.filter_var, value="exact", command=self._apply_filter).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(filter_frame, text="Visuels", variable=self.filter_var, value="visual", command=self._apply_filter).pack(side=tk.LEFT, padx=6)

        # Zone scrollable
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        canvas = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scroll_frame = ttk.Frame(canvas)
        self.scroll_window = canvas.create_window((0, 0), window=self.scroll_frame, anchor=tk.NW)

        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.scroll_window, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._canvas = canvas
        self._exact_groups: list[list[Path]] = []
        self._visual_groups: list[list[Path]] = []

    # ------------------------------------------------------------------ public

    def on_duplicates_found(self, exact: list[list[Path]], visual: list[list[Path]]):
        self._exact_groups = exact
        self._visual_groups = visual
        self._render_groups()

    def _render_groups(self):
        # Supprimer les anciens widgets
        for w in self._group_widgets:
            w.destroy()
        self._group_widgets.clear()

        flt = self.filter_var.get()
        groups_to_show = []
        if flt in ("all", "exact"):
            groups_to_show += [("exact", g) for g in self._exact_groups]
        if flt in ("all", "visual"):
            groups_to_show += [("visual", g) for g in self._visual_groups]

        total_exact = len(self._exact_groups)
        total_visual = len(self._visual_groups)
        self.label_summary.config(
            text=f"{total_exact} groupe(s) exacts, {total_visual} groupe(s) visuels"
            if (total_exact + total_visual) > 0 else "Aucun doublon détecté."
        )

        for idx, (gtype, group) in enumerate(groups_to_show):
            widget = DuplicateGroup(self.scroll_frame, group, gtype, idx)
            widget.pack(fill=tk.X, padx=4, pady=4)
            self._group_widgets.append(widget)

        if groups_to_show:
            self.btn_delete.config(state=tk.NORMAL)
        else:
            self.btn_delete.config(state=tk.DISABLED)

    def _apply_filter(self):
        self._render_groups()

    def _deselect_all(self):
        for w in self._group_widgets:
            for var in w.check_vars:
                var.set(False)

    def _delete_selected(self):
        to_delete: list[Path] = []
        for w in self._group_widgets:
            to_delete.extend(w.get_selected_paths())

        if not to_delete:
            messagebox.showinfo("Aucune sélection", "Aucun fichier sélectionné pour la suppression.")
            return

        if not messagebox.askyesno(
            "Confirmer la suppression",
            f"{len(to_delete)} fichier(s) seront déplacés dans le dossier '_corbeille'.\n\n"
            "Cette opération est réversible (les fichiers restent dans _corbeille).\n\nConfirmer ?",
        ):
            return

        dest = self.app.state["dest_dir"]
        if not dest:
            messagebox.showerror("Erreur", "Aucun dossier destination configuré.")
            return

        trash_dir = Path(dest) / "_corbeille"
        threading.Thread(
            target=self._run_trash, args=(to_delete, trash_dir), daemon=True
        ).start()

    def _run_trash(self, paths: list[Path], trash_dir: Path):
        from core.duplicate_finder import move_to_trash

        moved, errors = move_to_trash(paths, trash_dir)
        self.app.queue.put({
            "kind": "trash_done",
            "moved": moved,
            "original_paths": paths,   # chemins d'origine pour mettre à jour state["photos"]
            "errors": errors,
        })
        self.app.queue.put({
            "kind": "log",
            "text": f"Corbeille : {len(moved)} fichier(s) déplacés, {len(errors)} erreur(s).",
            "level": "success" if not errors else "warning",
        })
        # Rafraîchit l'affichage
        self.app.after(0, self._refresh_after_trash, paths)

    def _refresh_after_trash(self, deleted_paths: set):
        deleted_set = set(deleted_paths)
        for gtype in ("exact", "visual"):
            attr = f"_{gtype}_groups"
            new_groups = []
            for group in getattr(self, attr):
                remaining = [p for p in group if p not in deleted_set]
                if len(remaining) > 1:
                    new_groups.append(remaining)
            setattr(self, attr, new_groups)
        self._render_groups()
