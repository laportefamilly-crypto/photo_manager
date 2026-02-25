"""Détection des doublons : par MD5 (exact) et hash perceptuel (visuel)."""
import logging
from pathlib import Path
from typing import Callable

from core.utils import md5_hash, is_raw

logger = logging.getLogger("photo_manager")


def _group_by_size(photos: list[Path]) -> dict[int, list[Path]]:
    """Premier filtre rapide : regroupe les fichiers par taille."""
    groups: dict[int, list[Path]] = {}
    for p in photos:
        try:
            size = p.stat().st_size
            groups.setdefault(size, []).append(p)
        except OSError:
            pass
    return {s: g for s, g in groups.items() if len(g) > 1}


def find_exact_duplicates(
    photos: list[Path],
    progress_callback: Callable[[int, int, str], None] | None = None,
    stop_flag: list[bool] | None = None,
) -> list[list[Path]]:
    """
    Trouve les doublons exacts via MD5.

    Returns:
        Liste de groupes, chaque groupe contient ≥ 2 Path identiques.
    """
    stop_flag = stop_flag or [False]
    size_groups = _group_by_size(photos)
    candidates = [p for g in size_groups.values() for p in g]
    total = len(candidates)

    hash_map: dict[str, list[Path]] = {}
    for i, path in enumerate(candidates):
        if stop_flag[0]:
            break
        if progress_callback:
            progress_callback(i, total, str(path))
        try:
            h = md5_hash(path)
            hash_map.setdefault(h, []).append(path)
        except OSError as e:
            logger.warning("Impossible de hasher %s : %s", path, e)

    return [g for g in hash_map.values() if len(g) > 1]


def find_visual_duplicates(
    photos: list[Path],
    threshold: int = 10,
    progress_callback: Callable[[int, int, str], None] | None = None,
    stop_flag: list[bool] | None = None,
) -> list[list[Path]]:
    """
    Trouve les doublons visuels via dhash (imagehash).
    Ignore les fichiers RAW si Pillow ne peut pas les lire.

    Args:
        photos: Fichiers à analyser.
        threshold: Distance de Hamming max pour considérer deux images similaires.

    Returns:
        Liste de groupes de photos visuellement similaires.
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        logger.error("imagehash ou Pillow non installé.")
        return []

    stop_flag = stop_flag or [False]
    hashes: list[tuple[Path, object]] = []
    total = len(photos)

    for i, path in enumerate(photos):
        if stop_flag[0]:
            break
        if progress_callback:
            progress_callback(i, total, str(path))
        if is_raw(path):
            continue
        try:
            with Image.open(path) as img:
                h = imagehash.dhash(img)
            hashes.append((path, h))
        except Exception as e:
            logger.debug("Impossible de calculer le dhash pour %s : %s", path, e)

    # Regroupement par distance de Hamming
    used = set()
    groups: list[list[Path]] = []

    for i, (p1, h1) in enumerate(hashes):
        if i in used:
            continue
        group = [p1]
        for j, (p2, h2) in enumerate(hashes[i + 1 :], start=i + 1):
            if j in used:
                continue
            if abs(h1 - h2) <= threshold:
                group.append(p2)
                used.add(j)
        if len(group) > 1:
            used.add(i)
            groups.append(group)

    return groups


def move_to_trash(paths: list[Path], trash_dir: Path) -> tuple[list[Path], list[tuple[Path, str]]]:
    """
    Déplace les fichiers vers trash_dir au lieu de les supprimer définitivement.

    Returns:
        (moved, errors) avec moved = liste des Path déplacés.
    """
    import shutil

    trash_dir.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []
    errors: list[tuple[Path, str]] = []

    for path in paths:
        try:
            dest = trash_dir / path.name
            # Évite les collisions
            counter = 1
            while dest.exists():
                dest = trash_dir / f"{path.stem}_{counter}{path.suffix}"
                counter += 1
            shutil.move(str(path), str(dest))
            moved.append(dest)
            logger.info("Mis en corbeille : %s → %s", path.name, dest)
        except Exception as e:
            logger.error("Erreur corbeille pour %s : %s", path, e)
            errors.append((path, str(e)))

    return moved, errors
