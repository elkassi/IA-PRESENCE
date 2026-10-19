"""
Camera Widget — Widget flux caméra live avec thread séparé.

Affiche le flux vidéo de la webcam dans un label CustomTkinter,
avec superposition des bounding boxes et noms des visages détectés.
Le traitement vidéo s'exécute dans un thread dédié pour ne pas
bloquer l'interface graphique.
"""

import logging
import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import COLORS, FRAME_SKIP

logger = logging.getLogger(__name__)


class CameraWidget(ctk.CTkFrame):
    """Widget de flux caméra live avec détection faciale.

    Le flux vidéo tourne dans un thread séparé. Les résultats de
    détection sont passés au callback ``on_face_detected``.

    Attributes:
        _video_label: Label affichant le flux vidéo.
        _cap: Capture vidéo OpenCV.
        _running: Flag de contrôle du thread.
        _thread: Thread de capture vidéo.
        _face_callback: Callback appelé à chaque détection.
        _face_engine: Moteur de reconnaissance faciale (optionnel).
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        face_engine=None,
        on_face_detected: Optional[Callable] = None,
        width: int = 640,
        height: int = 480,
        **kwargs,
    ) -> None:
        """Initialise le widget caméra.

        Args:
            master: Widget parent.
            face_engine: Instance de ``FaceEngine`` pour la détection.
            on_face_detected: Callback ``(results: list[dict])`` appelé
                              à chaque détection de visage.
            width: Largeur du widget en pixels.
            height: Hauteur du widget en pixels.
        """
        super().__init__(
            master,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )

        self._width = width
        self._height = height
        self._face_engine = face_engine
        self._face_callback = on_face_detected
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_image = None
        self._last_notified: dict[str, float] = {}
        self._notify_cooldown_sec = 30.0
        self._detection_enabled = True

        # Label vidéo
        self._video_label = ctk.CTkLabel(
            self,
            text="📷 Caméra en attente…",
            font=ctk.CTkFont(size=16),
            text_color=COLORS["text_muted"],
            width=width,
            height=height,
        )
        self._video_label.pack(padx=10, pady=10)

        # Label de statut
        self._status_label = ctk.CTkLabel(
            self,
            text="⏸ Arrêtée",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._status_label.pack(pady=(0, 10))

        logger.info("CameraWidget initialisé (%dx%d).", width, height)

    def start(self) -> None:
        """Démarre le flux caméra dans un thread séparé."""
        if self._running:
            logger.warning("La caméra est déjà en cours d'exécution.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._status_label.configure(text="🔴 En direct", text_color=COLORS["success"])
        logger.info("Flux caméra démarré.")

    def stop(self) -> None:
        """Arrête le flux caméra."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
        self._status_label.configure(text="⏸ Arrêtée", text_color=COLORS["text_muted"])
        logger.info("Flux caméra arrêté.")

    def _capture_loop(self) -> None:
        """Boucle de capture vidéo (exécutée dans un thread séparé).

        Capture les frames, exécute la détection faciale, et met à jour
        l'affichage via ``after()`` pour la thread-safety de Tkinter.
        """
        try:
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                logger.error("Impossible d'ouvrir la webcam.")
                self._update_status_safe("❌ Webcam non disponible")
                self._running = False
                return

            logger.info("Webcam ouverte avec succès.")

            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    logger.warning("Frame non lue.")
                    time.sleep(0.1)
                    continue

                # Détection faciale (si moteur disponible et non en pause)
                results = []
                if self._face_engine and self._detection_enabled:
                    try:
                        results = self._face_engine.detect_and_identify(frame)
                    except Exception as e:
                        logger.error("Erreur détection : %s", e)

                # Dessiner les résultats sur le frame
                annotated_frame = self._draw_results(frame, results)

                # Mettre à jour l'affichage (thread-safe)
                self._update_frame_safe(annotated_frame)

                # Notifier le callback (éviter les appels répétés pour le même nom)
                if results and self._face_callback:
                    try:
                        filtered = self._filter_results_for_callback(results)
                        if filtered:
                            self._face_callback(filtered)
                    except Exception as e:
                        logger.error("Erreur callback détection : %s", e)

                # Petit délai pour ne pas surcharger le CPU
                time.sleep(0.03)

        except Exception as e:
            logger.error("Erreur dans la boucle de capture : %s", e)
        finally:
            if self._cap and self._cap.isOpened():
                self._cap.release()
            self._running = False

    def _filter_results_for_callback(self, results: list[dict]) -> list[dict]:
        """Limite les notifications aux visages reconnus (cooldown local).

        Args:
            results: Résultats bruts du FaceEngine.

        Returns:
            Sous-ensemble à transmettre au callback présence.
        """
        now = time.time()
        filtered: list[dict] = []
        for result in results:
            name = result.get("name", "Inconnu")
            if name == "Inconnu":
                continue
            last = self._last_notified.get(name, 0.0)
            if now - last >= self._notify_cooldown_sec:
                self._last_notified[name] = now
                filtered.append(result)
        return filtered

    def _draw_results(
        self, frame: np.ndarray, results: list[dict]
    ) -> np.ndarray:
        """Dessine les bounding boxes et noms sur le frame.

        Args:
            frame: Image BGR originale.
            results: Résultats de détection du FaceEngine.

        Returns:
            Frame annoté.
        """
        annotated = frame.copy()

        for result in results:
            name = result.get("name", "Inconnu")
            confidence = result.get("confidence", 0.0)
            bbox = result.get("bbox", (0, 0, 0, 0))
            x, y, w, h = bbox

            # Couleur selon la reconnaissance
            if name != "Inconnu":
                color = (16, 185, 129)  # Vert (#10b981) en BGR
                label = f"{name} ({confidence:.0%})"
            else:
                color = (0, 0, 255)  # Rouge
                label = "Inconnu"

            # Rectangle
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)

            # Label avec fond
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(
                annotated,
                (x, y - label_size[1] - 10),
                (x + label_size[0] + 10, y),
                color, -1,
            )
            cv2.putText(
                annotated, label,
                (x + 5, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2,
            )

        return annotated

    def _update_frame_safe(self, frame: np.ndarray) -> None:
        """Met à jour le label vidéo de manière thread-safe.

        Args:
            frame: Image BGR à afficher.
        """
        try:
            # Convertir BGR → RGB, redimensionner
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb = cv2.resize(rgb, (self._width, self._height))
            img = Image.fromarray(rgb)
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img,
                                      size=(self._width, self._height))

            # Mise à jour thread-safe via after()
            self._video_label.after(0, self._set_image, ctk_image)
        except Exception as e:
            logger.error("Erreur mise à jour frame : %s", e)

    def _set_image(self, ctk_image) -> None:
        """Applique l'image au label (appelé dans le thread principal).

        Args:
            ctk_image: Image CTk à afficher.
        """
        try:
            self._current_image = ctk_image  # Empêcher le garbage collection
            self._video_label.configure(image=ctk_image, text="")
        except Exception:
            pass

    def _update_status_safe(self, text: str) -> None:
        """Met à jour le label de statut de manière thread-safe.

        Args:
            text: Texte de statut.
        """
        try:
            self._status_label.after(
                0, self._status_label.configure,
                {"text": text, "text_color": COLORS["warning"]},
            )
        except Exception:
            pass

    def set_detection_enabled(self, enabled: bool) -> None:
        """Active/désactive la reconnaissance (le flux vidéo continue)."""
        self._detection_enabled = enabled

    def is_running(self) -> bool:
        """Vérifie si la caméra est en cours d'exécution.

        Returns:
            ``True`` si le flux est actif.
        """
        return self._running

    def __del__(self) -> None:
        """Nettoyage lors de la destruction."""
        self.stop()
