"""Système de design — dark SaaS palette inspirée du design HTML de référence."""
import tkinter as tk
from tkinter import ttk

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0a0a0f"   # fond général
SURFACE  = "#13131a"   # cartes
SURFACE2 = "#16161f"   # éléments imbriqués
BORDER   = "#1e1e2e"   # bordures subtiles
TEXT     = "#e8e8f0"   # texte principal
MUTED    = "#6b6b80"   # texte secondaire

PURPLE = "#6c63ff"     # accent principal
PINK   = "#ff6584"     # accent danger / secondaire
GREEN  = "#43e97b"     # accent succès
ORANGE = "#f7971e"     # accent avertissement
BLUE   = "#38bdf8"     # accent info

LOG_BG = "#080810"     # fond terminal

# ── Fonts ─────────────────────────────────────────────────────────────────────
F_DISPLAY = ("Segoe UI",  26, "bold")   # grands chiffres métriques
F_TITLE   = ("Segoe UI",  15, "bold")   # titre de page
F_HEADING = ("Segoe UI",  11, "bold")   # titres de section
F_BODY    = ("Segoe UI",  10)
F_SMALL   = ("Segoe UI",   9)
F_TINY    = ("Segoe UI",   8)
F_MONO    = ("Consolas",   9)
F_MONO_SM = ("Consolas",   8)


def apply(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=BG)

    # Frames
    style.configure("TFrame",        background=BG)
    style.configure("Card.TFrame",   background=SURFACE)
    style.configure("Card2.TFrame",  background=SURFACE2)

    # Labels
    style.configure("TLabel",        background=BG,       foreground=TEXT,  font=F_BODY)
    style.configure("Card.TLabel",   background=SURFACE,  foreground=TEXT,  font=F_BODY)
    style.configure("Muted.TLabel",  background=SURFACE,  foreground=MUTED, font=F_SMALL)
    style.configure("Muted2.TLabel", background=BG,       foreground=MUTED, font=F_SMALL)
    style.configure("Heading.TLabel",background=SURFACE,  foreground=TEXT,  font=F_HEADING)

    # Notebook — onglets sombres style SaaS
    style.configure("TNotebook",
        background=SURFACE, borderwidth=0, tabmargins=0)
    style.configure("TNotebook.Tab",
        background=SURFACE, foreground=MUTED,
        padding=[20, 11], font=("Segoe UI", 10),
        borderwidth=0,
    )
    style.map("TNotebook.Tab",
        background=[("selected", BG),    ("active", "#0f0f18")],
        foreground=[("selected", PURPLE), ("active", TEXT)],
    )

    # Boutons
    _btn_base = dict(relief="flat", borderwidth=0, padding=[12, 7])
    style.configure("TButton",
        background=SURFACE2, foreground=TEXT, font=F_BODY, **_btn_base)
    style.map("TButton",
        background=[("active", BORDER)], foreground=[("active", TEXT)])

    style.configure("Primary.TButton",
        background=PURPLE, foreground="#fff",
        font=("Segoe UI", 10, "bold"), **_btn_base)
    style.map("Primary.TButton",
        background=[("active", "#5a52d5")])

    style.configure("Danger.TButton",
        background=PINK, foreground="#fff", font=F_BODY, **_btn_base)
    style.map("Danger.TButton",
        background=[("active", "#d94f6e")])

    style.configure("Ghost.TButton",
        background=BG, foreground=MUTED,
        font=F_SMALL, padding=[8, 5], relief="flat", borderwidth=0)
    style.map("Ghost.TButton",
        background=[("active", SURFACE2)],
        foreground=[("active", TEXT)])

    # Progressbar
    style.configure("TProgressbar",
        troughcolor=BORDER, background=PURPLE,
        thickness=5, borderwidth=0)

    # Scrollbar
    style.configure("TScrollbar",
        background=BORDER, troughcolor=SURFACE,
        borderwidth=0, arrowsize=10, relief="flat")
    style.map("TScrollbar",
        background=[("active", MUTED)])

    # Entry / Spinbox
    for w in ("TEntry", "TSpinbox"):
        style.configure(w,
            fieldbackground=SURFACE2, foreground=TEXT,
            bordercolor=BORDER, insertcolor=PURPLE,
            font=F_BODY, selectbackground=PURPLE,
            selectforeground="#fff")

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton",
        background=SURFACE, foreground=TEXT, font=F_BODY)
    style.map("TCheckbutton", background=[("active", SURFACE)])

    style.configure("TRadiobutton",
        background=BG, foreground=MUTED, font=F_SMALL)
    style.map("TRadiobutton",
        background=[("active", BG)],
        foreground=[("active", TEXT)])

    return style


# ── Composants réutilisables ──────────────────────────────────────────────────

def card(parent, **kw) -> tk.Frame:
    """Panneau sombre avec bordure subtile."""
    return tk.Frame(parent, bg=SURFACE,
                    highlightbackground=BORDER, highlightthickness=1, **kw)


def badge(parent, text: str, color: str = PURPLE, bg: str = SURFACE) -> tk.Label:
    """Petite étiquette colorée style pill."""
    # Fond avec 20% opacité simulé par mélange de couleurs
    bg_light = _blend(color, bg, 0.15)
    return tk.Label(parent, text=text, bg=bg_light, fg=color,
                    font=F_TINY, padx=8, pady=2)


def metric_cell(parent, value: str, label: str, color: str = TEXT, bg: str = SURFACE):
    """Cellule de métrique : grand chiffre + libellé."""
    f = tk.Frame(parent, bg=bg)
    tk.Label(f, text=value, bg=bg, fg=color, font=F_DISPLAY).pack()
    tk.Label(f, text=label, bg=bg, fg=MUTED,  font=F_SMALL).pack()
    return f


def divider(parent, bg: str = SURFACE, horizontal=True) -> tk.Frame:
    if horizontal:
        return tk.Frame(parent, bg=BORDER, height=1)
    return tk.Frame(parent, bg=BORDER, width=1)


def _blend(hex_color: str, hex_bg: str, alpha: float) -> str:
    """Mélange deux couleurs hex avec un facteur alpha."""
    def parse(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
    r1,g1,b1 = parse(hex_color)
    r2,g2,b2 = parse(hex_bg)
    r = int(r1*alpha + r2*(1-alpha))
    g = int(g1*alpha + g2*(1-alpha))
    b = int(b1*alpha + b2*(1-alpha))
    return f"#{r:02x}{g:02x}{b:02x}"
