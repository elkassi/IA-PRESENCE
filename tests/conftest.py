"""
Conftest — Fixtures partagées pour les tests IA-PRESENCE.

Fournit des instances pré-configurées de DatabaseManager,
AuthManager, FaceEngine (mocké), et des données de test.
"""

import os
import sys
import tempfile

import numpy as np
import pytest

# Ajouter le répertoire racine au path
ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Fournit un chemin temporaire pour la base de données de test.

    Returns:
        Chemin vers un fichier SQLite temporaire.
    """
    return str(tmp_path / "test_presence.db")


@pytest.fixture
def db_manager(tmp_db_path):
    """Fournit une instance DatabaseManager avec BDD temporaire.

    Returns:
        Instance de DatabaseManager.
    """
    from database.db_manager import DatabaseManager
    db = DatabaseManager(db_path=tmp_db_path)
    yield db
    db.close()


@pytest.fixture
def sample_employee(db_manager):
    """Ajoute un employé de test et retourne ses infos.

    Returns:
        Dict avec les infos de l'employé.
    """
    employee_id = db_manager.add_employee("Test User", "IT")
    return {
        "id": employee_id,
        "name": "Test User",
        "department": "IT",
    }


@pytest.fixture
def sample_embedding():
    """Fournit un embedding numpy de test (512 dimensions).

    Returns:
        Vecteur numpy aléatoire de dimension 512.
    """
    np.random.seed(42)
    return np.random.rand(512).astype(np.float64)


@pytest.fixture
def tmp_employees_dir(tmp_path):
    """Crée un répertoire temporaire pour les données employés.

    Returns:
        Chemin vers le répertoire temporaire.
    """
    employees_dir = tmp_path / "employees"
    employees_dir.mkdir()
    return str(employees_dir)


@pytest.fixture
def tmp_exports_dir(tmp_path):
    """Crée un répertoire temporaire pour les exports.

    Returns:
        Chemin vers le répertoire temporaire.
    """
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    return str(exports_dir)
