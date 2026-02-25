"""Fenêtre principale de Photo Manager."""
import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from gui.config_tab import ConfigTab
from gui.scan_tab import ScanTab
from gui.duplicates_tab import DuplicatesTab
from gui.report_tab import ReportTab


CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class PhotoManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Manager")
        self.geometry("950x680")
        self.minsize(800, 580)
        self.configure(bg="#f0f0f0")

        # État partagé entre onglets
        self.state = {
            "source_dirs": [],
            "dest_dir": None,
            "move_files": tk.BooleanVar(value=False),
            "similarity_threshold": tk.IntVar(value=10),
            "photos": [],               # list[Path] trouvées
            "organized": [],            # list[Path] organisées
            "exact_duplicates": [],     # list[list[Path]]
            "visual_duplicates": [],    # list[list[Path]]
            "trash_moved": [],          # list[Path] mises en corbeille
            "errors": [],               # list[tuple[Path, str]]
        }

        # Queue pour communication threads → GUI
        self.queue: queue.Queue = queue.Queue()
        self.stop_flag = [False]

        self._build_ui()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()

    def _build_ui(self):
        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 10))
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.config_tab = ConfigTab(self.notebook, self)
        self.scan_tab = ScanTab(self.notebook, self)
        self.duplicates_tab = DuplicatesTab(self.notebook, self)
        self.report_tab = ReportTab(self.notebook, self)

        self.notebook.add(self.config_tab, text="  ⚙ Configuration  ")
        self.notebook.add(self.scan_tab, text="  🔍 Scan & Organisation  ")
        self.notebook.add(self.duplicates_tab, text="  🗂 Doublons  ")
        self.notebook.add(self.report_tab, text="  📊 Rapport  ")

        # Barre de statut
        self.status_var = tk.StringVar(value="Prêt.")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=(0, 4))

    def _poll_queue(self):
        """Vide la queue de messages des threads worker à intervalles réguliers."""
        try:
            while True:
                msg = self.queue.get_nowait()
                self._dispatch(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _dispatch(self, msg: dict):
        """Achemine un message vers le bon onglet ou action."""
        kind = msg.get("kind")
        if kind == "log":
            self.scan_tab.append_log(msg["text"], msg.get("level", "info"))
        elif kind == "progress":
            self.scan_tab.update_progress(msg["value"], msg["maximum"], msg.get("label", ""))
        elif kind == "status":
            self.status_var.set(msg["text"])
        elif kind == "scan_done":
            self.state["photos"] = msg["photos"]
            self.state["errors"] = msg.get("errors", [])
            self.scan_tab.on_scan_done(msg)
        elif kind == "organize_done":
            self.state["organized"] = msg["organized"]
            self.state["errors"] += msg.get("errors", [])
            # Mettre à jour la liste des photos pour que la recherche de doublons
            # travaille sur les fichiers à leur emplacement réel après organisation.
            if self.state["move_files"].get():
                # Déplacement : les anciens chemins n'existent plus, on remplace
                self.state["photos"] = list(msg["organized"])
                self.scan_tab.append_log(
                    f"Liste mise à jour : {len(self.state['photos'])} photos (chemins après déplacement).",
                    "info",
                )
            else:
                # Copie : originaux + copies dans la destination → on fusionne
                existing = set(self.state["photos"])
                new_copies = [p for p in msg["organized"] if p not in existing]
                self.state["photos"] = self.state["photos"] + new_copies
                self.scan_tab.append_log(
                    f"Liste mise à jour : {len(self.state['photos'])} photos "
                    f"(originaux + {len(new_copies)} copie(s) organisée(s)).",
                    "info",
                )
            self.scan_tab.on_organize_done(msg)
        elif kind == "duplicates_done":
            self.state["exact_duplicates"] = msg["exact"]
            self.state["visual_duplicates"] = msg["visual"]
            self.duplicates_tab.on_duplicates_found(msg["exact"], msg["visual"])
            self.scan_tab.on_duplicates_done(msg)
        elif kind == "trash_done":
            self.state["trash_moved"] += msg.get("moved", [])
            self.state["errors"] += msg.get("errors", [])
            # Retirer les fichiers mis en corbeille de la liste des photos
            # pour éviter des erreurs si l'on relance Organiser ensuite.
            trashed = set(msg.get("original_paths", []))
            self.state["photos"] = [p for p in self.state["photos"] if p not in trashed]
            self.report_tab.refresh()
        elif kind == "error":
            self.scan_tab.append_log(f"ERREUR : {msg['text']}", "error")

    def _load_config(self):
        """Charge la dernière configuration depuis config.json."""
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            self.state["move_files"].set(data.get("move_files", False))
            self.state["similarity_threshold"].set(data.get("similarity_threshold", 10))
            self.config_tab.load_config(data)
        except Exception:
            pass  # fichier corrompu → on ignore silencieusement

    def _save_config(self):
        """Sauvegarde la configuration courante dans config.json.
        Lit directement les widgets pour capturer ce qui est saisi,
        même si l'utilisateur n'a pas cliqué sur Valider.
        """
        try:
            sources = list(self.config_tab.src_listbox.get(0, "end"))
            dest = self.config_tab.dest_var.get().strip()
            data = {
                "source_dirs": sources,
                "dest_dir": dest,
                "move_files": self.state["move_files"].get(),
                "similarity_threshold": self.state["similarity_threshold"].get(),
            }
            CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.destroy()

    def set_status(self, text: str):
        self.status_var.set(text)

    def switch_to_tab(self, index: int):
        self.notebook.select(index)
