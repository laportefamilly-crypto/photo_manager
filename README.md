# Photo Manager

Logiciel de gestion et d'organisation de photos avec interface graphique (tkinter).

## Fonctionnalités

- **Scan récursif** de un ou plusieurs dossiers source
- **Organisation par date** : copie ou déplace les photos vers `Destination/YYYY/MM - Mois/`
  - Lit la date EXIF (`DateTimeOriginal`) en priorité
  - Fallback sur la date de modification du fichier
- **Détection de doublons**
  - Exacts : via hash MD5 (contenu identique, quel que soit le nom)
  - Visuels : via hash perceptuel dhash avec seuil de similarité configurable
- **Suppression sécurisée** : les fichiers sont déplacés dans un dossier `_corbeille/` (jamais supprimés définitivement)
- **Persistance de la configuration** : les dossiers et options sont sauvegardés entre les sessions
- **Export de rapport** : statistiques et erreurs exportables en TXT

## Formats supportés

JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC — ainsi que les formats RAW : CR2, CR3, NEF, ARW, DNG, ORF, RAF, et autres.

## Installation

**Prérequis** : Python 3.10+

```bash
git clone https://github.com/laportefamilly-crypto/photo_manager.git
cd photo_manager
pip install -r requirements.txt
python main.py
```

## Dépendances

| Package | Rôle |
|---------|------|
| `Pillow` | Lecture des images et métadonnées EXIF |
| `imagehash` | Hash perceptuel (dhash) pour les doublons visuels |
| `exifread` | Lecture EXIF étendue (formats RAW) |

## Utilisation

### 1. Configuration
Ajoutez un ou plusieurs dossiers source, choisissez le dossier destination, et configurez les options (copier/déplacer, seuil de similarité).

### 2. Scan & Organisation
- **Scanner** : parcourt récursivement les dossiers source et liste toutes les photos trouvées
- **Organiser par date** : copie ou déplace les photos dans une arborescence `YYYY/MM - Mois/`
- **Chercher les doublons** : détecte les doublons exacts (MD5) puis visuels (dhash)

### 3. Doublons
Les paires de doublons s'affichent avec aperçu miniature côte à côte. Sélectionnez les fichiers à supprimer puis cliquez sur "Supprimer la sélection" — ils sont déplacés dans `_corbeille/`.

### 4. Rapport
Statistiques de session (photos trouvées, organisées, doublons, erreurs) exportables en fichier TXT.

## Structure du projet

```
photo_manager/
├── main.py                    # Point d'entrée
├── requirements.txt
├── core/
│   ├── utils.py               # Extensions supportées, hashing MD5, logging
│   ├── scanner.py             # Scan récursif
│   ├── organizer.py           # Organisation par date EXIF
│   └── duplicate_finder.py    # Détection MD5 + dhash, mise en corbeille
└── gui/
    ├── app.py                 # Fenêtre principale, gestion des threads
    ├── config_tab.py          # Onglet Configuration
    ├── scan_tab.py            # Onglet Scan & Organisation
    ├── duplicates_tab.py      # Onglet Doublons
    └── report_tab.py          # Onglet Rapport
```
