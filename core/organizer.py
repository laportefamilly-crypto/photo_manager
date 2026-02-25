"""Organisation des photos par date dans la destination."""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from core.utils import MONTH_NAMES

logger = logging.getLogger("photo_manager")


def _read_exif_date(path: Path) -> datetime | None:
    """Tente de lire DateTimeOriginal depuis les métadonnées EXIF."""
    # 1) Pillow — DateTimeOriginal (0x9003) est dans le sous-IFD EXIF (0x8769)
    try:
        from PIL import Image

        _EXIF_IFD_TAG = 0x8769          # pointeur vers le sous-IFD EXIF
        _DATE_TIME_ORIGINAL = 0x9003    # DateTimeOriginal
        _DATE_TIME_TAG = 0x0132         # DateTime (fallback moins précis)

        with Image.open(path) as img:
            exif = img.getexif()
            if exif:
                # Cherche d'abord dans le sous-IFD EXIF
                exif_ifd = exif.get_ifd(_EXIF_IFD_TAG)
                date_str = exif_ifd.get(_DATE_TIME_ORIGINAL)
                if not date_str:
                    # Fallback : tag DateTime dans l'IFD principal
                    date_str = exif.get(_DATE_TIME_TAG)
                if date_str:
                    return datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass

    # 2) exifread (fallback, meilleure couverture RAW)
    try:
        import exifread

        with open(path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
        tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTimeOriginal")
        if tag:
            return datetime.strptime(str(tag), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass

    return None


def get_photo_date(path: Path) -> datetime:
    """
    Retourne la date de la photo.
    Priorité : EXIF DateTimeOriginal > date de modification du fichier.
    """
    date = _read_exif_date(path)
    if date:
        return date
    mtime = os.path.getmtime(path)
    return datetime.fromtimestamp(mtime)


def _build_dest_path(dest_root: Path, date: datetime, filename: str) -> Path:
    """Construit le chemin de destination : dest_root/YYYY/MM - Mois/filename."""
    year_folder = str(date.year)
    month_folder = MONTH_NAMES[date.month]
    return dest_root / year_folder / month_folder / filename


def _safe_dest(dest: Path) -> Path:
    """Si dest existe déjà, ajoute un suffixe _1, _2, …"""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize_photos(
    photos: list[Path],
    dest_root: Path,
    move: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
    stop_flag: list[bool] | None = None,
) -> dict:
    """
    Copie (ou déplace) les photos dans dest_root organisé par date.

    Returns:
        dict avec clés : 'organized' (list[Path]), 'errors' (list[tuple[Path, str]])
    """
    stop_flag = stop_flag or [False]
    organized: list[Path] = []
    errors: list[tuple[Path, str]] = []
    total = len(photos)

    for i, src in enumerate(photos):
        if stop_flag[0]:
            logger.info("Organisation interrompue.")
            break

        if progress_callback:
            progress_callback(i, total, str(src))

        try:
            date = get_photo_date(src)
            dest = _safe_dest(_build_dest_path(dest_root, date, src.name))
            dest.parent.mkdir(parents=True, exist_ok=True)

            if move:
                shutil.move(str(src), str(dest))
                action = "Déplacé"
            else:
                shutil.copy2(str(src), str(dest))
                action = "Copié"

            logger.debug("%s : %s → %s", action, src.name, dest)
            organized.append(dest)

        except Exception as e:
            logger.error("Erreur pour %s : %s", src, e)
            errors.append((src, str(e)))

    if progress_callback:
        progress_callback(total, total, "Terminé")

    logger.info("Organisation terminée : %d organisées, %d erreurs.", len(organized), len(errors))
    return {"organized": organized, "errors": errors}
