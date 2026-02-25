"""Utilitaires partagés : extensions, hashing, logging."""
import hashlib
import logging
from pathlib import Path

# Extensions photo supportées
PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic", ".heif",
    # RAW
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng",
    ".orf", ".pef", ".ptx", ".rw2", ".rwl", ".srw", ".x3f", ".raf",
}

# Extensions RAW (Pillow ne peut généralement pas les lire)
RAW_EXTENSIONS = {
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng",
    ".orf", ".pef", ".ptx", ".rw2", ".rwl", ".srw", ".x3f", ".raf",
}

# Noms de mois en français
MONTH_NAMES = {
    1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars",
    4: "04 - Avril", 5: "05 - Mai", 6: "06 - Juin",
    7: "07 - Juillet", 8: "08 - Août", 9: "09 - Septembre",
    10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre",
}


def setup_logging(log_file: Path | None = None) -> logging.Logger:
    """Configure et retourne le logger principal."""
    logger = logging.getLogger("photo_manager")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def md5_hash(path: Path, chunk_size: int = 65536) -> str:
    """Calcule le hash MD5 d'un fichier par blocs."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def is_photo(path: Path) -> bool:
    """Retourne True si le fichier est une photo supportée."""
    return path.suffix.lower() in PHOTO_EXTENSIONS


def is_raw(path: Path) -> bool:
    """Retourne True si le fichier est un format RAW."""
    return path.suffix.lower() in RAW_EXTENSIONS


def format_size(size_bytes: int) -> str:
    """Formate une taille en octets de façon lisible."""
    for unit in ("o", "Ko", "Mo", "Go"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} To"
