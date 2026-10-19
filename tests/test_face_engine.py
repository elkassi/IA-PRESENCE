"""
Tests — FaceEngine.

Teste le moteur de reconnaissance faciale : distance cosinus,
chargement d'embeddings, et détection (avec mocks DeepFace).
"""

import os
import sys
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)


class TestFaceEngineCosineDistance:
    """Tests pour la distance cosinus (méthode statique)."""

    def test_identical_vectors(self):
        """Vecteurs identiques → distance 0."""
        from core.face_engine import FaceEngine
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        dist = FaceEngine._cosine_distance(a, b)
        assert abs(dist) < 1e-6

    def test_orthogonal_vectors(self):
        """Vecteurs orthogonaux → distance 1."""
        from core.face_engine import FaceEngine
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        dist = FaceEngine._cosine_distance(a, b)
        assert abs(dist - 1.0) < 1e-6

    def test_opposite_vectors(self):
        """Vecteurs opposés → distance 2."""
        from core.face_engine import FaceEngine
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        dist = FaceEngine._cosine_distance(a, b)
        assert abs(dist - 2.0) < 1e-6

    def test_zero_vector(self):
        """Vecteur nul → distance 1 (fallback)."""
        from core.face_engine import FaceEngine
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        dist = FaceEngine._cosine_distance(a, b)
        assert dist == 1.0

    def test_similar_vectors(self):
        """Vecteurs similaires → petite distance."""
        from core.face_engine import FaceEngine
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.1, 2.1, 3.1])
        dist = FaceEngine._cosine_distance(a, b)
        assert dist < 0.01


class TestFaceEngineInit:
    """Tests pour l'initialisation du FaceEngine."""

    @patch("core.face_engine.os.path.exists", return_value=False)
    @patch("core.face_engine.os.listdir", return_value=[])
    def test_no_employees_dir(self, mock_listdir, mock_exists):
        """Initialisation sans dossier employés → 0 embeddings."""
        with patch.dict("sys.modules", {"deepface": MagicMock(), "deepface.DeepFace": MagicMock()}):
            from core.face_engine import FaceEngine
            engine = FaceEngine()
            assert engine.employee_count == 0

    def test_employee_count_property(self):
        """La propriété employee_count retourne le bon nombre."""
        with patch.dict("sys.modules", {"deepface": MagicMock(), "deepface.DeepFace": MagicMock()}):
            from core.face_engine import FaceEngine
            engine = FaceEngine()
            engine._embeddings = {"Alice": np.zeros(512), "Bob": np.zeros(512)}
            assert engine.employee_count == 2
