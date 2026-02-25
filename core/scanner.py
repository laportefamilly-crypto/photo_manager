"""Scan récursif des dossiers pour trouver les photos."""
import logging
from pathlib import Path
from typing import Callable

from core.utils import is_photo

logger = logging.getLogger("photo_manager")


def scan_folders(
    source_dirs: list[Path],
    progress_callback: Callable[[int, int, str], None] | None = None,
    stop_flag: list[bool] | None = None,
) -> list[Path]:
    """
    Scanne récursivement les dossiers source.

    Args:
        source_dirs: Liste des dossiers à scanner.
        progress_callback: Appelé avec (nb_trouvées, -1, chemin_actuel).
        stop_flag: Liste d'un booléen ; si stop_flag[0] est True, on arrête.

    Returns:
        Liste des Path de photos trouvées.
    """
    photos: list[Path] = []
    stop_flag = stop_flag or [False]

    for source in source_dirs:
        source = Path(source)
        if not source.exists():
            logger.warning("Dossier introuvable : %s", source)
            continue
        if not source.is_dir():
            logger.warning("Pas un dossier : %s", source)
            continue

        logger.info("Scan de : %s", source)

        for path in source.rglob("*"):
            if stop_flag[0]:
                logger.info("Scan interrompu par l'utilisateur.")
                return photos

            if not path.is_file():
                continue

            if progress_callback:
                progress_callback(len(photos), -1, str(path))

            if is_photo(path):
                photos.append(path)
                logger.debug("Trouvé : %s", path)

    logger.info("Scan terminé : %d photos trouvées.", len(photos))
    return photos
