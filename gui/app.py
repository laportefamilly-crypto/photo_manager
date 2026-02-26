"""Fenêtre principale — dark SaaS style."""
import json
import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import gui.theme as th
from gui.config_tab import ConfigTab
from gui.scan_tab import ScanTab
from gui.duplicates_tab import DuplicatesTab
from gui.report_tab import ReportTab

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class PhotoManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Manager")
        self.geometry("1020x720")
        self.minsize(840, 600)

        self.state = {
            "source_dirs": [],
            "dest_dir": None,
            "move_files": tk.BooleanVar(value=False),
            "similarity_threshold": tk.IntVar(value=10),
            "photos": [],
            "organized": [],
            "exact_duplicates": [],
            "visual_duplicates": [],
            "trash_moved": [],
            "errors": [],
        }

        self.queue: queue.Queue = queue.Queue()
        self.stop_flag = [False]

        th.apply(self)
        self._build_ui()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=th.SURFACE,
                          highlightbackground=th.BORDER, highlightthickness=1)
        header.pack(fill=tk.X)

        h_inner = tk.Frame(header, bg=th.SURFACE)
        h_inner.pack(fill=tk.X, padx=24, pady=14)

        # Logo / titre
        logo_frame = tk.Frame(h_inner, bg=th.SURFACE)
        logo_frame.pack(side=tk.LEFT)

        # Icône colorée
        icon = tk.Label(logo_frame, text="◈", bg=th.PURPLE, fg="#fff",
                        font=("Segoe UI", 13, "bold"), padx=8, pady=4)
        icon.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(logo_frame, text="Photo Manager",
                 bg=th.SURFACE, fg=th.TEXT, font=("Segoe UI", 13, "bold")).pack(
                 side=tk.LEFT)
        tk.Label(logo_frame, text="  ·  Organisez vos photos",
                 bg=th.SURFACE, fg=th.MUTED, font=th.F_SMALL).pack(
                 side=tk.LEFT, padx=(0, 0))

        # Statut à droite
        status_right = tk.Frame(h_inner, bg=th.SURFACE)
        status_right.pack(side=tk.RIGHT)

        self._status_dot = tk.Label(status_right, text="●",
                                    bg=th.SURFACE, fg=th.GREEN, font=("Segoe UI", 10))
        self._status_dot.pack(side=tk.LEFT, padx=(0, 4))

        self.status_var = tk.StringVar(value="Prêt")
        tk.Label(status_right, textvariable=self.status_var,
                 bg=th.SURFACE, fg=th.MUTED, font=th.F_SMALL).pack(side=tk.LEFT)

        # ── Notebook ─────────────────────────────────────────────────────────
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.config_tab     = ConfigTab(self.notebook, self)
        self.scan_tab       = ScanTab(self.notebook, self)
        self.duplicates_tab = DuplicatesTab(self.notebook, self)
        self.report_tab     = ReportTab(self.notebook, self)

        self.notebook.add(self.config_tab,     text="  Configuration  ")
        self.notebook.add(self.scan_tab,       text="  Scan & Organisation  ")
        self.notebook.add(self.duplicates_tab, text="  Doublons  ")
        self.notebook.add(self.report_tab,     text="  Rapport  ")

    # ── Queue ─────────────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                self._dispatch(self.queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _dispatch(self, msg: dict):
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
            if self.state["move_files"].get():
                self.state["photos"] = list(msg["organized"])
                self.scan_tab.append_log(
                    f"Liste mise à jour : {len(self.state['photos'])} photos.", "info")
            else:
                existing = set(self.state["photos"])
                new_copies = [p for p in msg["organized"] if p not in existing]
                self.state["photos"] = self.state["photos"] + new_copies
                self.scan_tab.append_log(
                    f"Liste mise à jour : {len(self.state['photos'])} photos "
                    f"(+{len(new_copies)} copie(s)).", "info")
            self.scan_tab.on_organize_done(msg)
        elif kind == "duplicates_done":
            self.state["exact_duplicates"] = msg["exact"]
            self.state["visual_duplicates"] = msg["visual"]
            self.duplicates_tab.on_duplicates_found(msg["exact"], msg["visual"])
            self.scan_tab.on_duplicates_done(msg)
        elif kind == "trash_done":
            self.state["trash_moved"] += msg.get("moved", [])
            self.state["errors"]      += msg.get("errors", [])
            trashed = set(msg.get("original_paths", []))
            self.state["photos"] = [p for p in self.state["photos"] if p not in trashed]
            self.report_tab.refresh()
        elif kind == "error":
            self.scan_tab.append_log(f"ERREUR : {msg['text']}", "error")

    # ── Config persistence ────────────────────────────────────────────────────

    def _load_config(self):
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            self.state["move_files"].set(data.get("move_files", False))
            self.state["similarity_threshold"].set(data.get("similarity_threshold", 10))
            self.config_tab.load_config(data)
        except Exception:
            pass

    def _save_config(self):
        try:
            data = {
                "source_dirs": list(self.config_tab.src_listbox.get(0, "end")),
                "dest_dir":    self.config_tab.dest_var.get().strip(),
                "move_files":  self.state["move_files"].get(),
                "similarity_threshold": self.state["similarity_threshold"].get(),
            }
            CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def set_status(self, text: str, color: str = th.GREEN):
        self.status_var.set(text)
        self._status_dot.configure(fg=color)

    def switch_to_tab(self, index: int):
        self.notebook.select(index)
