"""
Face Engine — Module de reconnaissance faciale temps réel.

Utilise DeepFace + FaceNet512 pour identifier les employés via webcam.

Performances cibles :
    - < 150ms par frame de traitement
    - > 85% de taux de reconnaissance correcte
    - < 2% de faux positifs
"""

import os
import logging
import threading
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    DISTANCE_THRESHOLD,
    FRAME_SKIP,
    FACE_MODEL,
    FACE_DETECTOR,
    EMPLOYEES_DIR,
)
from security.embedding_cipher import EmbeddingCipher

logger = logging.getLogger(__name__)


class FaceEngine:
    """Moteur de reconnaissance faciale basé sur DeepFace / FaceNet512.

    Attributes:
        _model_name: Nom du modèle DeepFace utilisé.
        _detector: Nom du détecteur de visages.
        _threshold: Seuil de distance pour la reconnaissance.
        _frame_count: Compteur de frames pour le skip.
        _embeddings: Dict {nom_employé: np.ndarray} des embeddings chargés.
        _cipher: Instance EmbeddingCipher pour déchiffrer les embeddings.
        _last_results: Derniers résultats de détection (cache entre frames skippés).
    """

    def __init__(self) -> None:
        """Charge les modèles DeepFace et les embeddings de référence."""
        self._model_name = FACE_MODEL
        self._detector = FACE_DETECTOR
        self._threshold = DISTANCE_THRESHOLD
        self._frame_count = 0
        self._cipher = EmbeddingCipher()
        self._embeddings: dict[str, np.ndarray] = {}
        self._last_results: list[dict] = []
        self._infer_lock = threading.Lock()

        # Pré-charger DeepFace (import différé pour performance)
        try:
            from deepface import DeepFace
            self._deepface = DeepFace
            logger.info(
                "FaceEngine initialisé (modèle=%s, détecteur=%s, seuil=%.2f).",
                self._model_name, self._detector, self._threshold,
            )
        except ImportError as e:
            logger.error("DeepFace non installé : %s", e)
            self._deepface = None

        # Charger les embeddings existants
        self.load_employee_embeddings()
        self._warmup_model()

    def _warmup_model(self) -> None:
        """Pré-charge le modèle DeepFace pour éviter un long blocage au 1er enrôlement."""
        if self._deepface is None:
            return
        try:
            import tempfile
            # Image minimale 64×64 (visage non requis avec enforce_detection=False)
            blank = np.zeros((64, 64, 3), dtype=np.uint8)
            blank[20:44, 20:44] = 128
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            cv2.imwrite(tmp_path, blank)
            try:
                logger.info("Pré-chargement du modèle IA (peut prendre 1 à 3 min)…")
                self._deepface.represent(
                    img_path=tmp_path,
                    model_name=self._model_name,
                    detector_backend=self._detector,
                    enforce_detection=False,
                )
                logger.info("Modèle IA prêt.")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            logger.warning("Pré-chargement IA ignoré : %s", e)

    def load_employee_embeddings(self) -> dict[str, np.ndarray]:
        """Charge et déchiffre tous les embeddings des employés.

        Parcourt le dossier ``data/employees/`` et déchiffre chaque
        fichier ``embedding.enc``.

        Returns:
            Dict ``{nom_employé: embedding_numpy}``.
        """
        self._embeddings = {}

        if not os.path.exists(EMPLOYEES_DIR):
            logger.warning("Dossier employés introuvable : %s", EMPLOYEES_DIR)
            return self._embeddings

        for employee_name in os.listdir(EMPLOYEES_DIR):
            employee_dir = os.path.join(EMPLOYEES_DIR, employee_name)
            embedding_path = os.path.join(employee_dir, "embedding.enc")

            if not os.path.isdir(employee_dir) or not os.path.exists(embedding_path):
                continue

            try:
                with open(embedding_path, "rb") as f:
                    encrypted_data = f.read()
                embedding = self._cipher.decrypt(encrypted_data)
                self._embeddings[employee_name] = embedding
                logger.info("Embedding chargé pour : %s", employee_name)
            except Exception as e:
                logger.error(
                    "Impossible de charger l'embedding de '%s' : %s",
                    employee_name, e,
                )

        logger.info("Total embeddings chargés : %d", len(self._embeddings))
        return self._embeddings

    def detect_and_identify(
        self, frame: np.ndarray, apply_frame_skip: bool = True
    ) -> list[dict]:
        """Analyse un frame webcam et retourne les visages identifiés.

        Applique le frame-skip (1 frame sur ``FRAME_SKIP``) et retourne
        les résultats mis en cache pour les frames ignorés.

        Args:
            frame: Image BGR capturée par OpenCV.
            apply_frame_skip: Si ``True`` (défaut), applique la règle
                ``FRAME_SKIP`` pour améliorer les performances. Mettre
                ``False`` pour forcer l'analyse (utile pour une image importée).

        Returns:
            Liste de dicts::

                {
                    "name": str,          # Nom de l'employé ou "Inconnu"
                    "confidence": float,  # Score de confiance (0.0 à 1.0)
                    "bbox": tuple,        # (x, y, w, h) bounding box
                    "timestamp": datetime
                }
        """
        self._frame_count += 1

        # Frame skip pour performance (désactivable, ex: analyse d'une image importée)
        if apply_frame_skip and self._frame_count % FRAME_SKIP != 0:
            return self._last_results

        if self._deepface is None:
            logger.warning("DeepFace non disponible, détection impossible.")
            return []

        start_time = time.perf_counter()
        results = []

        try:
            with self._infer_lock:
                return self._detect_and_identify_locked(frame, start_time)
        except Exception as e:
            logger.error("Erreur lors de la détection : %s", e)
            return []

    def _detect_and_identify_locked(
        self, frame: np.ndarray, start_time: float
    ) -> list[dict]:
        """Détection + identification (appelé sous verrou)."""
        results = []
        try:
            face_objs = self._deepface.extract_faces(
                img_path=frame,
                detector_backend=self._detector,
                enforce_detection=False,
            )

            for face_obj in face_objs:
                facial_area = face_obj.get("facial_area", {})
                x = facial_area.get("x", 0)
                y = facial_area.get("y", 0)
                w = facial_area.get("w", 0)
                h = facial_area.get("h", 0)

                # Ignorer les détections trop petites
                if w < 30 or h < 30:
                    continue

                # Extraire la région du visage
                face_region = frame[y:y + h, x:x + w]
                if face_region.size == 0:
                    continue

                # Identifier le visage
                name, confidence = self._identify_face(face_region)

                results.append({
                    "name": name,
                    "confidence": confidence,
                    "bbox": (x, y, w, h),
                    "timestamp": datetime.now(),
                })

                logger.info(
                    "Visage détecté : %s (confiance=%.2f, bbox=(%d,%d,%d,%d)).",
                    name, confidence, x, y, w, h,
                )

        except Exception as e:
            logger.error("Erreur lors de la détection (locked) : %s", e)

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.debug("Traitement frame en %.1f ms (%d visages).", elapsed, len(results))

        self._last_results = results
        return results

    def _identify_face(self, face_region: np.ndarray) -> tuple[str, float]:
        """Identifie un visage en le comparant aux embeddings enregistrés.

        Args:
            face_region: Image BGR du visage découpé.

        Returns:
            Tuple ``(nom, confiance)`` — ``("Inconnu", 0.0)`` si non reconnu.
        """
        if not self._embeddings:
            return ("Inconnu", 0.0)

        try:
            # Générer l'embedding du visage détecté
            embedding_objs = self._deepface.represent(
                img_path=face_region,
                model_name=self._model_name,
                detector_backend="skip",  # Visage déjà découpé
                enforce_detection=False,
            )

            if not embedding_objs:
                return ("Inconnu", 0.0)

            current_embedding = np.array(embedding_objs[0]["embedding"])

            # Comparer avec tous les embeddings enregistrés
            best_name = "Inconnu"
            best_distance = float("inf")

            for emp_name, ref_embedding in self._embeddings.items():
                distance = self._cosine_distance(current_embedding, ref_embedding)
                if distance < best_distance:
                    best_distance = distance
                    best_name = emp_name

            # Vérifier le seuil
            if best_distance <= self._threshold:
                confidence = max(0.0, min(1.0, 1.0 - best_distance))
                return (best_name, confidence)
            else:
                return ("Inconnu", 0.0)

        except Exception as e:
            logger.error("Erreur lors de l'identification : %s", e)
            return ("Inconnu", 0.0)

    @staticmethod
    def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Calcule la distance cosinus entre deux vecteurs.

        Args:
            a: Premier vecteur.
            b: Second vecteur.

        Returns:
            Distance cosinus (0.0 = identique, 2.0 = opposé).
        """
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 1.0
        return 1.0 - (dot / (norm_a * norm_b))

    def generate_embedding(self, photo_path: str) -> Optional[np.ndarray]:
        """Génère un embedding FaceNet512 pour une photo d'enrôlement.

        Args:
            photo_path: Chemin vers le fichier image.

        Returns:
            Vecteur numpy de l'embedding ou ``None`` en cas d'échec.
        """
        if self._deepface is None:
            logger.error("DeepFace non disponible.")
            return None

        try:
            with self._infer_lock:
                embedding_objs = self._deepface.represent(
                    img_path=photo_path,
                    model_name=self._model_name,
                    detector_backend=self._detector,
                    enforce_detection=False,
                )
            if embedding_objs:
                embedding = np.array(embedding_objs[0]["embedding"])
                logger.info("Embedding généré pour : %s", photo_path)
                return embedding
            else:
                logger.warning("Aucun visage détecté dans : %s", photo_path)
                return None
        except Exception as e:
            logger.error("Erreur génération embedding (%s) : %s", photo_path, e)
            return None

    @property
    def employee_count(self) -> int:
        """Nombre d'employés avec embeddings chargés."""
        return len(self._embeddings)
