"""Onglet Scan & Organisation — dark SaaS."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import gui.theme as th


class ScanTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(style="TFrame")
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Barre d'actions ───────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=th.SURFACE,
                           highlightbackground=th.BORDER, highlightthickness=1)
        toolbar.grid(row=0, column=0, sticky="ew")

        tb_inner = tk.Frame(toolbar, bg=th.SURFACE)
        tb_inner.pack(fill=tk.X, padx=20, pady=12)

        self.btn_scan = ttk.Button(tb_inner, text="⬡  Scanner",
                                   style="Primary.TButton", command=self._start_scan)
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_organize = ttk.Button(tb_inner, text="Organiser par date",
                                       command=self._start_organize, state=tk.DISABLED)
        self.btn_organize.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_duplicates = ttk.Button(tb_inner, text="Chercher les doublons",
                                         command=self._start_duplicates, state=tk.DISABLED)
        self.btn_duplicates.pack(side=tk.LEFT)

        self.btn_stop = ttk.Button(tb_inner, text="Arrêter",
                                   style="Danger.TButton",
                                   command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT)

        # ── Progression ───────────────────────────────────────────────────────
        prog_card = th.card(self)
        prog_card.grid(row=1, column=0, sticky="ew", padx=20, pady=12)

        prog_inner = tk.Frame(prog_card, bg=th.SURFACE)
        prog_inner.pack(fill=tk.X, padx=20, pady=14)

        top_row = tk.Frame(prog_inner, bg=th.SURFACE)
        top_row.pack(fill=tk.X, pady=(0, 6))

        self.progress_label = tk.Label(top_row, text="En attente…",
                                       bg=th.SURFACE, fg=th.MUTED, font=th.F_SMALL)
        self.progress_label.pack(side=tk.LEFT)

        self.progress_count = tk.Label(top_row, text="",
                                       bg=th.SURFACE, fg=th.PURPLE, font=th.F_SMALL)
        self.progress_count.pack(side=tk.RIGHT)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(prog_inner, variable=self.progress_var,
                                            mode="determinate")
        self.progress_bar.pack(fill=tk.X)

        # ── Journal ───────────────────────────────────────────────────────────
        log_container = tk.Frame(self, bg=th.BG)
        log_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 16))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(1, weight=1)

        log_header = tk.Frame(log_container, bg=th.BG)
        log_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        tk.Label(log_header, text="Journal", bg=th.BG,
                 fg=th.TEXT, font=th.F_HEADING).pack(side=tk.LEFT)

        # Badge "LIVE" animé
        self._live_badge = tk.Label(log_header,
            text="● LIVE", bg=th._blend(th.GREEN, th.BG, 0.15),
            fg=th.GREEN, font=th.F_TINY, padx=8, pady=2)
        self._live_badge.pack(side=tk.LEFT, padx=8)

        ttk.Button(log_header, text="Effacer", style="Ghost.TButton",
                   command=self._clear_log).pack(side=tk.RIGHT)

        self.log_text = tk.Text(
            log_container, wrap=tk.WORD, state=tk.DISABLED,
            font=th.F_MONO, bg=th.LOG_BG, fg="#94a3b8",
            insertbackground=th.PURPLE,
            relief="flat", borderwidth=0,
            padx=14, pady=10,
            selectbackground=th._blend(th.PURPLE, th.LOG_BG, 0.3),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

        log_scroll = ttk.Scrollbar(log_container, command=self.log_text.yview)
        log_scroll.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # Tags de couleur pour le journal
        self.log_text.tag_configure("info",    foreground="#64748b")
        self.log_text.tag_configure("success", foreground=th.GREEN)
        self.log_text.tag_configure("warning", foreground=th.ORANGE)
        self.log_text.tag_configure("error",   foreground=th.PINK)
        self.log_text.tag_configure("section", foreground=th.PURPLE,
                                    font=("Consolas", 9, "bold"))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _check_config(self) -> bool:
        if not self.app.state["source_dirs"] or not self.app.state["dest_dir"]:
            messagebox.showwarning("Configuration manquante",
                "Configurez les dossiers dans l'onglet Configuration.")
            self.app.switch_to_tab(0)
            return False
        return True

    def _start_scan(self):
        if not self._check_config(): return
        self.app.stop_flag[0] = False
        self._set_running(True)
        self._progress_indeterminate()
        self.append_log("── Démarrage du scan ──", "section")
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        from core.scanner import scan_folders
        q = self.app.queue
        def cb(found, _t, path):
            q.put({"kind": "progress", "value": 0, "maximum": 0,
                   "label": f"Scan en cours… {found} photos"})
        try:
            photos = scan_folders(self.app.state["source_dirs"],
                                  progress_callback=cb, stop_flag=self.app.stop_flag)
            q.put({"kind": "scan_done", "photos": photos, "errors": []})
        except Exception as e:
            q.put({"kind": "error", "text": str(e)})
            q.put({"kind": "scan_done", "photos": [], "errors": [(None, str(e))]})

    def _start_organize(self):
        if not self.app.state["photos"]:
            messagebox.showinfo("Scan requis", "Lancez d'abord un scan.")
            return
        move = self.app.state["move_files"].get()
        action = "déplacer" if move else "copier"
        if not messagebox.askyesno("Confirmer",
            f"Voulez-vous {action} {len(self.app.state['photos'])} photos "
            f"vers :\n{self.app.state['dest_dir']} ?"):
            return
        self.app.stop_flag[0] = False
        self._set_running(True)
        self.append_log("── Organisation par date ──", "section")
        threading.Thread(target=self._run_organize, daemon=True).start()

    def _run_organize(self):
        from core.organizer import organize_photos
        q = self.app.queue
        def cb(i, t, _):
            q.put({"kind": "progress", "value": i, "maximum": t,
                   "label": f"Organisation {i} / {t}"})
        try:
            result = organize_photos(
                self.app.state["photos"],
                dest_root=self.app.state["dest_dir"],
                move=self.app.state["move_files"].get(),
                progress_callback=cb, stop_flag=self.app.stop_flag)
            q.put({"kind": "organize_done", **result})
        except Exception as e:
            q.put({"kind": "error", "text": str(e)})
            q.put({"kind": "organize_done", "organized": [], "errors": [(None, str(e))]})

    def _start_duplicates(self):
        if not self.app.state["photos"]:
            messagebox.showinfo("Scan requis", "Lancez d'abord un scan.")
            return
        self.app.stop_flag[0] = False
        self._set_running(True)
        self.append_log("── Recherche des doublons ──", "section")
        threading.Thread(target=self._run_duplicates, daemon=True).start()

    def _run_duplicates(self):
        from core.duplicate_finder import find_exact_duplicates, find_visual_duplicates
        q = self.app.queue
        photos = self.app.state["photos"]
        threshold = self.app.state["similarity_threshold"].get()
        def cb_e(i, t, _): q.put({"kind": "progress", "value": i, "maximum": t, "label": f"MD5 {i}/{t}"})
        def cb_v(i, t, _): q.put({"kind": "progress", "value": i, "maximum": t, "label": f"Dhash {i}/{t}"})
        try:
            q.put({"kind": "log", "text": "Calcul des hash MD5…", "level": "info"})
            exact = find_exact_duplicates(photos, progress_callback=cb_e, stop_flag=self.app.stop_flag)
            q.put({"kind": "log", "text": f"{len(exact)} groupe(s) exacts.", "level": "success"})

            exact_paths = {p for g in exact for p in g}
            photos_v = [p for p in photos if p not in exact_paths]

            q.put({"kind": "log", "text": "Calcul des hash perceptuels (dhash)…", "level": "info"})
            visual = find_visual_duplicates(photos_v, threshold=threshold,
                                            progress_callback=cb_v, stop_flag=self.app.stop_flag)
            q.put({"kind": "log", "text": f"{len(visual)} groupe(s) visuels.", "level": "success"})
            q.put({"kind": "duplicates_done", "exact": exact, "visual": visual})
        except Exception as e:
            q.put({"kind": "error", "text": str(e)})
            q.put({"kind": "duplicates_done", "exact": [], "visual": []})

    def _stop(self):
        self.app.stop_flag[0] = True
        self.append_log("Arrêt demandé…", "warning")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def on_scan_done(self, msg):
        n = len(msg["photos"])
        self._set_running(False); self._progress_done()
        self.append_log(f"Scan terminé — {n} photos trouvées.", "success")
        if n:
            self.btn_organize.config(state=tk.NORMAL)
            self.btn_duplicates.config(state=tk.NORMAL)
        self.app.set_status(f"Scan terminé — {n} photos")
        self.app.report_tab.refresh()

    def on_organize_done(self, msg):
        n, e = len(msg["organized"]), len(msg.get("errors", []))
        self._set_running(False); self._progress_done()
        self.append_log(f"Organisation terminée — {n} fichiers, {e} erreur(s).", "success")
        self.app.set_status(f"Organisation — {n} fichiers",
                            th.ORANGE if e else th.GREEN)
        self.app.report_tab.refresh()

    def on_duplicates_done(self, msg):
        exact, visual = msg["exact"], msg["visual"]
        self._set_running(False); self._progress_done()
        self.append_log(
            f"Recherche terminée — {len(exact)} exact(s), {len(visual)} visuel(s).", "success")
        self.app.set_status(f"Doublons : {len(exact)+len(visual)} groupes")
        self.app.switch_to_tab(2)
        self.app.report_tab.refresh()

    # ── UI helpers ────────────────────────────────────────────────────────────

    def append_log(self, text: str, level: str = "info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_progress(self, value: int, maximum: int, label: str = ""):
        if maximum <= 0:
            if self.progress_bar["mode"] != "indeterminate":
                self.progress_bar.config(mode="indeterminate")
                self.progress_bar.start(10)
        else:
            if self.progress_bar["mode"] != "determinate":
                self.progress_bar.stop()
                self.progress_bar.config(mode="determinate")
            self.progress_var.set(int(value / maximum * 100) if maximum else 0)
            self.progress_count.config(text=f"{value} / {maximum}")
        if label:
            self.progress_label.config(text=label)

    def _set_running(self, running: bool):
        on  = tk.DISABLED if running else tk.NORMAL
        off = tk.NORMAL   if running else tk.DISABLED
        for btn in (self.btn_scan, self.btn_organize, self.btn_duplicates):
            btn.config(state=on)
        self.btn_stop.config(state=off)
        self._live_badge.config(
            fg=th.GREEN if running else th.MUTED,
            bg=th._blend(th.GREEN if running else th.MUTED, th.BG, 0.15))

    def _progress_indeterminate(self):
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)
        self.progress_label.config(text="En cours…")
        self.progress_count.config(text="")

    def _progress_done(self):
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate")
        self.progress_var.set(100)
        self.progress_label.config(text="Terminé")

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
