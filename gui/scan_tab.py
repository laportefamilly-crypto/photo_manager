"""Onglet Scan & Organisation : progression, logs, lancement des tâches."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class ScanTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._worker: threading.Thread | None = None
        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 6}

        # === Boutons d'action ===
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, **pad)

        self.btn_scan = ttk.Button(btn_frame, text="🔍  Scanner les dossiers", command=self._start_scan, style="Accent.TButton")
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_organize = ttk.Button(btn_frame, text="📁  Organiser par date", command=self._start_organize, state=tk.DISABLED)
        self.btn_organize.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_duplicates = ttk.Button(btn_frame, text="🔎  Chercher les doublons", command=self._start_duplicates, state=tk.DISABLED)
        self.btn_duplicates.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ttk.Button(btn_frame, text="⏹  Arrêter", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT)

        # === Barre de progression ===
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, **pad)

        self.progress_label = ttk.Label(progress_frame, text="En attente…")
        self.progress_label.pack(anchor=tk.W)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var,
            mode="indeterminate", length=400,
        )
        self.progress_bar.pack(fill=tk.X, pady=4)

        self.progress_count = ttk.Label(progress_frame, text="")
        self.progress_count.pack(anchor=tk.W)

        # === Zone de logs ===
        log_frame = ttk.LabelFrame(self, text="Journal")
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.log_text = tk.Text(
            log_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # Tags de couleur
        self.log_text.tag_configure("info", foreground="#d4d4d4")
        self.log_text.tag_configure("success", foreground="#4ec9b0")
        self.log_text.tag_configure("warning", foreground="#ce9178")
        self.log_text.tag_configure("error", foreground="#f44747")

        ttk.Button(self, text="Effacer le journal", command=self._clear_log).pack(anchor=tk.E, padx=12, pady=4)

    # ------------------------------------------------------------------ actions

    def _check_config(self) -> bool:
        if not self.app.state["source_dirs"] or not self.app.state["dest_dir"]:
            messagebox.showwarning(
                "Configuration manquante",
                "Veuillez d'abord configurer les dossiers dans l'onglet Configuration.",
            )
            self.app.switch_to_tab(0)
            return False
        return True

    def _start_scan(self):
        if not self._check_config():
            return
        self.app.stop_flag[0] = False
        self._set_running(True)
        self._progress_indeterminate()
        self.append_log("=== Démarrage du scan ===", "success")
        self._worker = threading.Thread(target=self._run_scan, daemon=True)
        self._worker.start()

    def _run_scan(self):
        from core.scanner import scan_folders

        q = self.app.queue

        def cb(found, _total, path):
            q.put({"kind": "progress", "value": 0, "maximum": 0, "label": f"Scan… {found} photos"})
            q.put({"kind": "log", "text": f"Examiné : {Path(path).name}", "level": "info"})

        try:
            photos = scan_folders(
                self.app.state["source_dirs"],
                progress_callback=cb,
                stop_flag=self.app.stop_flag,
            )
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
        if not messagebox.askyesno(
            "Confirmer l'organisation",
            f"Voulez-vous {action} {len(self.app.state['photos'])} photos vers :\n{self.app.state['dest_dir']} ?",
        ):
            return
        self.app.stop_flag[0] = False
        self._set_running(True)
        self.append_log("=== Démarrage de l'organisation ===", "success")
        self._worker = threading.Thread(target=self._run_organize, daemon=True)
        self._worker.start()

    def _run_organize(self):
        from core.organizer import organize_photos

        q = self.app.queue
        photos = self.app.state["photos"]
        total = len(photos)

        def cb(i, t, path):
            q.put({"kind": "progress", "value": i, "maximum": t, "label": f"Organisation {i}/{t}"})
            if path != "Terminé":
                q.put({"kind": "log", "text": f"Traitement : {Path(path).name}", "level": "info"})

        try:
            result = organize_photos(
                photos,
                dest_root=self.app.state["dest_dir"],
                move=self.app.state["move_files"].get(),
                progress_callback=cb,
                stop_flag=self.app.stop_flag,
            )
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
        self.append_log("=== Recherche des doublons ===", "success")
        self._worker = threading.Thread(target=self._run_duplicates, daemon=True)
        self._worker.start()

    def _run_duplicates(self):
        from core.duplicate_finder import find_exact_duplicates, find_visual_duplicates

        q = self.app.queue
        photos = self.app.state["photos"]
        threshold = self.app.state["similarity_threshold"].get()

        def cb_exact(i, total, path):
            q.put({"kind": "progress", "value": i, "maximum": total, "label": f"MD5 {i}/{total}"})

        def cb_visual(i, total, path):
            q.put({"kind": "progress", "value": i, "maximum": total, "label": f"Dhash {i}/{total}"})

        try:
            q.put({"kind": "log", "text": "Calcul des hash MD5…", "level": "info"})
            exact = find_exact_duplicates(photos, progress_callback=cb_exact, stop_flag=self.app.stop_flag)
            q.put({"kind": "log", "text": f"{len(exact)} groupe(s) de doublons exacts trouvés.", "level": "success"})

            # Exclure les fichiers déjà groupés comme doublons exacts :
            # ils ont forcément un dhash identique (distance=0) donc seraient
            # détectés une 2e fois dans les doublons visuels.
            exact_paths = {p for group in exact for p in group}
            photos_for_visual = [p for p in photos if p not in exact_paths]

            q.put({"kind": "log", "text": "Calcul des hash perceptuels (dhash)…", "level": "info"})
            visual = find_visual_duplicates(photos_for_visual, threshold=threshold, progress_callback=cb_visual, stop_flag=self.app.stop_flag)
            q.put({"kind": "log", "text": f"{len(visual)} groupe(s) de doublons visuels trouvés.", "level": "success"})

            q.put({"kind": "duplicates_done", "exact": exact, "visual": visual})
        except Exception as e:
            q.put({"kind": "error", "text": str(e)})
            q.put({"kind": "duplicates_done", "exact": [], "visual": []})

    def _stop(self):
        self.app.stop_flag[0] = True
        self.append_log("Arrêt demandé…", "warning")

    # ------------------------------------------------------------------ callbacks

    def on_scan_done(self, msg: dict):
        photos = msg["photos"]
        self._set_running(False)
        self._progress_stop()
        self.append_log(f"✔ Scan terminé : {len(photos)} photos trouvées.", "success")
        if photos:
            self.btn_organize.config(state=tk.NORMAL)
            self.btn_duplicates.config(state=tk.NORMAL)
        self.app.set_status(f"Scan terminé — {len(photos)} photos.")
        self.app.report_tab.refresh()

    def on_organize_done(self, msg: dict):
        organized = msg["organized"]
        errors = msg.get("errors", [])
        self._set_running(False)
        self._progress_stop()
        self.append_log(f"✔ Organisation terminée : {len(organized)} photos traitées, {len(errors)} erreurs.", "success")
        self.app.set_status(f"Organisation terminée — {len(organized)} fichiers.")
        self.app.report_tab.refresh()

    def on_duplicates_done(self, msg: dict):
        self._set_running(False)
        self._progress_stop()
        exact = msg["exact"]
        visual = msg["visual"]
        total = sum(len(g) for g in exact) + sum(len(g) for g in visual)
        self.append_log(f"✔ Recherche terminée : {len(exact)} groupes exacts, {len(visual)} groupes visuels.", "success")
        self.app.set_status(f"Doublons : {len(exact)} exacts, {len(visual)} visuels.")
        self.app.switch_to_tab(2)
        self.app.report_tab.refresh()

    # ------------------------------------------------------------------ UI helpers

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
            self.progress_bar.config(maximum=100)
            self.progress_count.config(text=f"{value} / {maximum}")

        if label:
            self.progress_label.config(text=label)

    def _set_running(self, running: bool):
        state_on = tk.DISABLED if running else tk.NORMAL
        state_off = tk.NORMAL if running else tk.DISABLED
        self.btn_scan.config(state=state_on)
        self.btn_organize.config(state=state_on)
        self.btn_duplicates.config(state=state_on)
        self.btn_stop.config(state=state_off)

    def _progress_indeterminate(self):
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)
        self.progress_label.config(text="En cours…")
        self.progress_count.config(text="")

    def _progress_stop(self):
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=100)
        self.progress_var.set(100)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
