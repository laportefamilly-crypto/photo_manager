"""Point d'entrée de Photo Manager."""
import sys
from pathlib import Path

# Ajoute le dossier racine au chemin Python pour les imports absolus
sys.path.insert(0, str(Path(__file__).parent))

from core.utils import setup_logging
from gui.app import PhotoManagerApp


def main():
    log_file = Path(__file__).parent / "photo_manager.log"
    setup_logging(log_file)

    app = PhotoManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
