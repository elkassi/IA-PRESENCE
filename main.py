"""
IA-PRESENCE — Point d'entrée principal.

Lance le système de gestion de présence par reconnaissance faciale :
    1. Configure le logging.
    2. Crée les répertoires nécessaires.
    3. Initialise les managers (BDD, IA, Auth, Enrôlement, Export).
    4. Lance le dashboard CustomTkinter.

Usage::

    python main.py
"""

import os
import sys
import logging

# Ajouter le répertoire racine au path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Vérifier la disponibilité de Tkinter (requis par CustomTkinter)
try:
    import tkinter  # noqa: F401
except ModuleNotFoundError as e:
    print(
        "Erreur: Tkinter n'est pas disponible dans cet environnement.\n"
        "Cette application utilise une interface graphique (CustomTkinter).\n\n"
        "Solution (Linux): installez le paquet 'python3-tk' puis relancez.\n"
        "Solution (Windows/macOS): utilisez une installation Python qui inclut Tkinter.\n"
    )
    raise

from config import (
    LOG_LEVEL,
    LOG_FORMAT,
    DB_PATH,
    EMPLOYEES_DIR,
    EXPORTS_DIR,
    DEFAULT_CLASS_NUMBER,
)
from database.db_manager import DatabaseManager
from core.face_engine import FaceEngine
from core.auth_manager import AuthManager
from core.enrollment import EnrollmentManager
from export.excel_exporter import ExcelExporter
from ui.dashboard import Dashboard


def setup_logging() -> None:
    """Configure le logging global de l'application."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                os.path.join(BASE_DIR, "ia_presence.log"),
                encoding="utf-8",
            ),
        ],
    )


def create_directories() -> None:
    """Crée les répertoires nécessaires s'ils n'existent pas."""
    dirs = [
        os.path.dirname(DB_PATH),
        EMPLOYEES_DIR,
        EXPORTS_DIR,
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def main() -> None:
    """Point d'entrée principal de l'application IA-PRESENCE."""
    # 1. Logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("  IA-PRESENCE — Démarrage de l'application")
    logger.info("=" * 60)

    # 2. Répertoires
    create_directories()
    logger.info("Répertoires vérifiés.")

    # 3. Initialisation des managers
    logger.info("Initialisation des composants…")

    db_manager = DatabaseManager()
    logger.info("✅ DatabaseManager OK")

    face_engine = FaceEngine()
    logger.info("✅ FaceEngine OK (%d employés chargés)", face_engine.employee_count)

    auth_manager = AuthManager(db_manager, class_number=DEFAULT_CLASS_NUMBER)
    logger.info("✅ AuthManager OK")

    enrollment_manager = EnrollmentManager(face_engine, db_manager)
    logger.info("✅ EnrollmentManager OK")

    exporter = ExcelExporter(db_manager)
    logger.info("✅ ExcelExporter OK")

    # 4. Vérification intégrité BDD
    if db_manager.verify_integrity():
        logger.info("✅ Intégrité BDD vérifiée")
    else:
        logger.warning("⚠️ Problème d'intégrité BDD détecté")

    # 5. Lancement du dashboard
    logger.info("Lancement du dashboard…")
    app = Dashboard(
        db_manager=db_manager,
        face_engine=face_engine,
        auth_manager=auth_manager,
        enrollment_manager=enrollment_manager,
        exporter=exporter,
    )
    app.run()

    logger.info("Application fermée.")


if __name__ == "__main__":
    main()
