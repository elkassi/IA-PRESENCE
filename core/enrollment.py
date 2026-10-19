"""
Enrollment — Capture et génération des embeddings pour un nouvel employé.

Processus :
    1. Capture automatique de 50+ photos via webcam.
    2. Filtrage qualité (visage détecté, flou, luminosité).
    3. Génération embedding FaceNet512 (moyenne des embeddings).
    4. Chiffrement AES-256 et sauvegarde.

Temps cible : < 10 minutes pour un enrôlement complet.
"""

import os
import logging
import time
import shutil
from typing import Callable, Optional, Sequence

import cv2
import numpy as np

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PHOTOS_MIN_ENROLLMENT, EMPLOYEES_DIR
from core.face_engine import FaceEngine
from security.embedding_cipher import EmbeddingCipher
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class EnrollmentManager:
    """Gestionnaire d'enrôlement des employés.

    Attributes:
        _face_engine: Moteur de reconnaissance faciale.
        _cipher: Chiffreur d'embeddings.
        _db: Gestionnaire de base de données.
        _min_photos: Nombre minimum de photos requis.
    """

    def __init__(
        self,
        face_engine: FaceEngine,
        db_manager: DatabaseManager,
    ) -> None:
        """Initialise le gestionnaire d'enrôlement.

        Args:
            face_engine: Instance de ``FaceEngine``.
            db_manager: Instance de ``DatabaseManager``.
        """
        self._face_engine = face_engine
        self._cipher = EmbeddingCipher()
        self._db = db_manager
        self._min_photos = PHOTOS_MIN_ENROLLMENT
        logger.info("EnrollmentManager initialisé (min_photos=%d).", self._min_photos)

    def start_enrollment(
        self,
        employee_name: str,
        department: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> bool:
        """Lance l'enrôlement complet d'un employé.

        Args:
            employee_name: Nom complet de l'employé.
            department: Département (optionnel).
            progress_callback: Fonction ``(current, total, message)``
                               appelée à chaque étape.

        Returns:
            ``True`` si l'enrôlement est réussi, ``False`` sinon.
        """
        logger.info("Début de l'enrôlement (webcam) de '%s'.", employee_name)

        # Créer le dossier de l'employé
        employee_dir = os.path.join(EMPLOYEES_DIR, employee_name)
        photos_dir = os.path.join(employee_dir, "photos")
        os.makedirs(photos_dir, exist_ok=True)

        # Étape 1 : Capture des photos
        if progress_callback:
            progress_callback(0, self._min_photos, "Début de la capture photos…")

        photo_paths = self.capture_photos(
            save_dir=photos_dir,
            n_photos=self._min_photos,
            progress_callback=progress_callback,
        )

        if len(photo_paths) < self._min_photos:
            logger.error(
                "Enrôlement échoué : seulement %d/%d photos capturées.",
                len(photo_paths), self._min_photos,
            )
            if progress_callback:
                progress_callback(
                    len(photo_paths), self._min_photos,
                    f"Échec : {len(photo_paths)}/{self._min_photos} photos.",
                )
            return False

        return self._finalize_enrollment(
            employee_name=employee_name,
            department=department,
            photo_paths=photo_paths,
            progress_callback=progress_callback,
            progress_total=self._min_photos,
        )

    def start_enrollment_from_photos(
        self,
        employee_name: str,
        photo_paths: Sequence[str],
        department: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        min_photos_required: int = 1,
    ) -> bool:
        """Enrôlement à partir de photos importées (sans webcam).

        Args:
            employee_name: Nom complet de l'employé.
            photo_paths: Chemins des images sélectionnées par l'utilisateur.
            department: Département (optionnel).
            progress_callback: Callback ``(current, total, message)``.
            min_photos_required: Nombre minimum de photos à exiger.
                Par défaut 1 (car l'utilisateur fournit déjà ses photos).

        Returns:
            ``True`` si l'enrôlement est réussi, ``False`` sinon.
        """
        photo_paths = [p for p in photo_paths if p]
        total = max(len(photo_paths), 1)

        logger.info(
            "Début de l'enrôlement (import) de '%s' (%d photos).",
            employee_name, len(photo_paths),
        )

        if len(photo_paths) < min_photos_required:
            if progress_callback:
                progress_callback(
                    len(photo_paths), min_photos_required,
                    f"⚠️ Sélectionnez au moins {min_photos_required} photo(s).",
                )
            return False

        # Copier les photos dans le dossier employé (pour garder un historique)
        employee_dir = os.path.join(EMPLOYEES_DIR, employee_name)
        photos_dir = os.path.join(employee_dir, "photos")
        os.makedirs(photos_dir, exist_ok=True)

        saved_paths: list[str] = []
        if progress_callback:
            progress_callback(0, total, "Copie des photos importées…")

        for idx, src in enumerate(photo_paths, 1):
            try:
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                dst = os.path.join(photos_dir, f"import_{idx:04d}{ext}")
                shutil.copy2(src, dst)
                saved_paths.append(dst)
                if progress_callback:
                    progress_callback(idx, total, f"Photo {idx}/{total} importée.")
            except Exception as e:
                logger.warning("Impossible d'importer %s : %s", src, e)

        if len(saved_paths) < min_photos_required:
            if progress_callback:
                progress_callback(
                    len(saved_paths), min_photos_required,
                    f"Échec import : {len(saved_paths)}/{min_photos_required} photo(s).",
                )
            return False

        return self._finalize_enrollment(
            employee_name=employee_name,
            department=department,
            photo_paths=saved_paths,
            progress_callback=progress_callback,
            progress_total=max(min_photos_required, len(saved_paths)),
        )

    def _finalize_enrollment(
        self,
        employee_name: str,
        department: str,
        photo_paths: list[str],
        progress_callback: Optional[Callable[[int, int, str], None]],
        progress_total: int,
    ) -> bool:
        """Étape finale commune : génération + sauvegarde + MAJ BDD."""
        # Étape : Générer et sauvegarder l'embedding
        if progress_callback:
            progress_callback(progress_total, progress_total, "Génération de l'embedding…")

        success = self.generate_and_save_embedding(
            employee_name, photo_paths, progress_callback=progress_callback
        )

        if success:
            # Ajouter l'employé en base de données
            try:
                self._db.add_employee(employee_name, department)
            except Exception:
                logger.info("Employé '%s' déjà en base.", employee_name)

            # Recharger les embeddings
            self._face_engine.load_employee_embeddings()

            if progress_callback:
                progress_callback(
                    progress_total, progress_total,
                    "Enrôlement terminé avec succès !",
                )
            logger.info("Enrôlement de '%s' terminé avec succès.", employee_name)

        return success

    def capture_photos(
        self,
        save_dir: str,
        n_photos: int = 50,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[str]:
        """Capture N photos filtrées par qualité via webcam.

        Applique des filtres de qualité :
            - Visage détecté dans le frame.
            - Image non floue (Laplacien > seuil).
            - Luminosité suffisante.

        Args:
            save_dir: Répertoire de sauvegarde des photos.
            n_photos: Nombre de photos à capturer.
            progress_callback: Fonction de progression.

        Returns:
            Liste des chemins des photos sauvegardées.
        """
        os.makedirs(save_dir, exist_ok=True)
        photo_paths: list[str] = []

        try:
            # Laisser la webcam principale se libérer complètement
            time.sleep(0.8)
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Impossible d'ouvrir la webcam.")
                return photo_paths

            logger.info("Webcam ouverte. Capture de %d photos…", n_photos)
            frame_count = 0
            max_attempts = n_photos * 5  # Max 5x tentatives

            while len(photo_paths) < n_photos and frame_count < max_attempts:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame non lue, nouvelle tentative…")
                    continue

                frame_count += 1

                # Sauter des frames pour varier les poses
                if frame_count % 3 != 0:
                    continue

                # Filtrage qualité
                if not self._check_quality(frame):
                    continue

                # Sauvegarder
                filename = f"photo_{len(photo_paths):04d}.jpg"
                filepath = os.path.join(save_dir, filename)
                cv2.imwrite(filepath, frame)
                photo_paths.append(filepath)

                if progress_callback:
                    progress_callback(
                        len(photo_paths), n_photos,
                        f"Photo {len(photo_paths)}/{n_photos} capturée.",
                    )

                logger.debug("Photo capturée : %s", filepath)

                # Petit délai pour varier les poses
                time.sleep(0.2)

        except Exception as e:
            logger.error("Erreur lors de la capture : %s", e)
        finally:
            if 'cap' in locals():
                cap.release()

        logger.info("Capture terminée : %d/%d photos.", len(photo_paths), n_photos)
        return photo_paths

    def _check_quality(self, frame: np.ndarray) -> bool:
        """Vérifie la qualité d'un frame pour l'enrôlement.

        Critères :
            - Détection d'au moins un visage (Haar Cascade).
            - Image non floue (variance du Laplacien > 100).
            - Luminosité suffisante (moyenne > 40).

        Args:
            frame: Image BGR capturée.

        Returns:
            ``True`` si le frame passe tous les filtres.
        """
        # Vérifier la luminosité
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        if brightness < 40:
            logger.debug("Frame trop sombre (luminosité=%.1f).", brightness)
            return False

        # Vérifier le flou (variance du Laplacien)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            logger.debug("Frame trop floue (laplacien=%.1f).", laplacian_var)
            return False

        # Vérifier la présence d'un visage
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            logger.debug("Aucun visage détecté dans le frame.")
            return False

        return True

    def generate_and_save_embedding(
        self,
        employee_name: str,
        photo_paths: list[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> bool:
        """Génère, chiffre et sauvegarde l'embedding final.

        Calcule la moyenne des embeddings de toutes les photos valides.

        Args:
            employee_name: Nom de l'employé.
            photo_paths: Liste des chemins vers les photos.
            progress_callback: Callback ``(current, total, message)``.

        Returns:
            ``True`` si l'embedding est généré et sauvegardé avec succès.
        """
        embeddings: list[np.ndarray] = []
        total = len(photo_paths)

        for i, photo_path in enumerate(photo_paths):
            if progress_callback:
                progress_callback(
                    i,
                    total,
                    (
                        f"Analyse IA {i + 1}/{total} — "
                        "première fois : 1 à 3 min possibles…"
                    ),
                )
            try:
                embedding = self._face_engine.generate_embedding(photo_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    logger.debug(
                        "Embedding %d/%d généré (%s).",
                        i + 1, len(photo_paths), photo_path,
                    )
            except Exception as e:
                logger.warning("Échec embedding pour %s : %s", photo_path, e)

        if not embeddings:
            logger.error("Aucun embedding valide généré pour '%s'.", employee_name)
            return False

        if progress_callback:
            progress_callback(total, total, "Calcul et chiffrement de l'embedding…")

        # Calcul de l'embedding moyen
        mean_embedding = np.mean(embeddings, axis=0)
        logger.info(
            "Embedding moyen calculé pour '%s' (%d/%d photos valides).",
            employee_name, len(embeddings), len(photo_paths),
        )

        # Chiffrer et sauvegarder
        try:
            encrypted = self._cipher.encrypt(mean_embedding)
            employee_dir = os.path.join(EMPLOYEES_DIR, employee_name)
            os.makedirs(employee_dir, exist_ok=True)
            embedding_path = os.path.join(employee_dir, "embedding.enc")

            with open(embedding_path, "wb") as f:
                f.write(encrypted)

            logger.info("Embedding chiffré sauvegardé : %s", embedding_path)
            return True
        except Exception as e:
            logger.error("Erreur lors de la sauvegarde : %s", e)
            return False
