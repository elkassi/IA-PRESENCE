"""
Dashboard — Interface principale IA-PRESENCE.

Fenêtre 1280×800 avec layout :
    - Top bar : logo, date/heure, boutons Export + Enrôler.
    - Zone gauche : flux caméra live.
    - Zone droite : liste des présences du jour.
    - Barre de stats : cartes Présents / IN TIME / LATE.
    - Status bar : résumé en bas.

Palette dark-navy avec accents violets.
"""

import logging
import threading
from datetime import datetime
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    COLORS,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    APP_TITLE,
    DEFAULT_CLASS_NUMBER,
)
from database.db_manager import DatabaseManager
from core.face_engine import FaceEngine
from core.auth_manager import AuthManager
from core.enrollment import EnrollmentManager
from export.excel_exporter import ExcelExporter
from ui.camera_widget import CameraWidget
from ui.history_panel import HistoryPanel
from ui.enrollment_ui import EnrollmentUI
from ui.photo_upload_ui import PhotoUploadUI
from ui.components.stat_card import StatCard
from ui.components.toast_notification import ToastManager

logger = logging.getLogger(__name__)

try:
    import cv2  # Optionnel : utilisé pour l'analyse d'images importées
except Exception:  # pragma: no cover
    cv2 = None


class Dashboard(ctk.CTk):
    """Dashboard principal de l'application IA-PRESENCE.

    Attributes:
        _db: Gestionnaire de base de données.
        _face_engine: Moteur de reconnaissance faciale.
        _auth_manager: Gestionnaire d'authentification.
        _enrollment_manager: Gestionnaire d'enrôlement.
        _exporter: Exporteur Excel.
        _camera: Widget caméra.
        _history: Panneau d'historique.
        _toast: Gestionnaire de toasts.
        _stat_cards: Cartes de statistiques.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        face_engine: FaceEngine,
        auth_manager: AuthManager,
        enrollment_manager: EnrollmentManager,
        exporter: ExcelExporter,
    ) -> None:
        """Initialise le dashboard.

        Args:
            db_manager: Gestionnaire BDD.
            face_engine: Moteur IA.
            auth_manager: Gestionnaire auth.
            enrollment_manager: Gestionnaire enrôlement.
            exporter: Exporteur Excel.
        """
        super().__init__()

        self._db = db_manager
        self._face_engine = face_engine
        self._auth_manager = auth_manager
        self._enrollment_manager = enrollment_manager
        self._exporter = exporter

        # Configuration fenêtre
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(1024, 700)
        self.configure(fg_color=COLORS["bg_primary"])

        # Apparence globale
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Toast manager
        self._toast = ToastManager(self)

        # Stat cards
        self._stat_cards: dict[str, StatCard] = {}
        self._camera_was_running = False

        # Construire l'UI
        self._build_ui()

        # Charger les données initiales
        self._refresh_data()

        # Timer horloge
        self._update_clock()

        # Timer rafraîchissement données (toutes les 10s)
        self._schedule_refresh()

        # Synchroniser le numéro de classe et démarrer la webcam
        self._on_class_changed()
        self.after(500, self._auto_start_camera)

        logger.info("Dashboard initialisé (%dx%d).", WINDOW_WIDTH, WINDOW_HEIGHT)

    def _build_ui(self) -> None:
        """Construit l'interface complète du dashboard."""
        self._build_topbar()
        self._build_main_content()
        self._build_stats_bar()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # Top Bar
    # ------------------------------------------------------------------

    def _build_topbar(self) -> None:
        """Construit la barre supérieure."""
        topbar = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            height=70,
            corner_radius=0,
        )
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        # Logo
        logo = ctk.CTkLabel(
            topbar,
            text="🔐 IA-PRESENCE",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["accent"],
        )
        logo.pack(side="left", padx=25)

        # Date et heure
        self._datetime_label = ctk.CTkLabel(
            topbar,
            text="",
            font=ctk.CTkFont(size=15),
            text_color=COLORS["text_muted"],
        )
        self._datetime_label.pack(side="left", padx=20)

        # Numéro de classe (pointages)
        class_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        class_frame.pack(side="right", padx=(0, 15))

        ctk.CTkLabel(
            class_frame,
            text="Classe :",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(0, 6))

        self._class_entry = ctk.CTkEntry(
            class_frame,
            width=60,
            height=36,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )
        self._class_entry.insert(0, DEFAULT_CLASS_NUMBER)
        self._class_entry.pack(side="left")
        self._class_entry.bind("<FocusOut>", self._on_class_changed)
        self._class_entry.bind("<Return>", self._on_class_changed)

        # Boutons (à droite)
        btn_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=20)

        # Bouton upload photos (gestionnaire)
        upload_btn = ctk.CTkButton(
            btn_frame,
            text="📤 Ajouter photos",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=10,
            command=self._open_photo_upload,
        )
        upload_btn.pack(side="right", padx=(10, 0))

        # Bouton Enrôler
        enroll_btn = ctk.CTkButton(
            btn_frame,
            text="➕ Enrôler",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=10,
            command=self._open_enrollment,
        )
        enroll_btn.pack(side="right", padx=(10, 0))

        # Bouton Export Excel
        export_btn = ctk.CTkButton(
            btn_frame,
            text="📊 Exporter Excel",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            command=self._export_excel,
        )
        export_btn.pack(side="right", padx=(10, 0))

        # Bouton Analyse Image (upload)
        analyze_btn = ctk.CTkButton(
            btn_frame,
            text="🖼️ Analyser photo",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            command=self._analyze_photo,
        )
        analyze_btn.pack(side="right", padx=(10, 0))

        # Bouton Caméra ON/OFF
        self._cam_btn = ctk.CTkButton(
            btn_frame,
            text="📷 Démarrer Caméra",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["success"],
            hover_color="#0d9668",
            corner_radius=10,
            command=self._toggle_camera,
        )
        self._cam_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Main Content (Camera + History)
    # ------------------------------------------------------------------

    def _build_main_content(self) -> None:
        """Construit la zone principale (caméra + historique)."""
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=(10, 5))

        # Colonne gauche : Caméra
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._camera = CameraWidget(
            left,
            face_engine=self._face_engine,
            on_face_detected=self._on_face_detected,
            width=580,
            height=420,
        )
        self._camera.pack(fill="both", expand=True)

        # Colonne droite : Historique
        right = ctk.CTkFrame(main, fg_color="transparent", width=400)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)

        self._history = HistoryPanel(right)
        self._history.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Stats Bar
    # ------------------------------------------------------------------

    def _build_stats_bar(self) -> None:
        """Construit la barre de statistiques."""
        stats = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=130,
        )
        stats.pack(fill="x", padx=15, pady=5)

        # Carte Présents
        self._stat_cards["total"] = StatCard(
            stats,
            icon="👥",
            value="0",
            label="Présents",
            accent_color=COLORS["accent"],
        )
        self._stat_cards["total"].pack(
            side="left", fill="both", expand=True, padx=(0, 10),
        )

        # Carte IN TIME
        self._stat_cards["in_time"] = StatCard(
            stats,
            icon="✅",
            value="0",
            label="IN TIME",
            accent_color=COLORS["success"],
        )
        self._stat_cards["in_time"].pack(
            side="left", fill="both", expand=True, padx=(0, 10),
        )

        # Carte LATE
        self._stat_cards["late"] = StatCard(
            stats,
            icon="🟡",
            value="0",
            label="LATE",
            accent_color=COLORS["warning"],
        )
        self._stat_cards["late"].pack(
            side="left", fill="both", expand=True, padx=(0, 10),
        )

        # Carte Employés enrôlés
        self._stat_cards["employees"] = StatCard(
            stats,
            icon="🔐",
            value=str(self._face_engine.employee_count),
            label="Employés enrôlés",
            accent_color=COLORS["text_muted"],
        )
        self._stat_cards["employees"].pack(
            side="left", fill="both", expand=True,
        )

    # ------------------------------------------------------------------
    # Status Bar
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        """Construit la barre de statut en bas."""
        statusbar = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            height=35,
            corner_radius=0,
        )
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)

        self._status_text = ctk.CTkLabel(
            statusbar,
            text="IA-PRESENCE v1.0 — EMSI 2025-2026 — Système prêt",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._status_text.pack(side="left", padx=20)

        self._cam_status = ctk.CTkLabel(
            statusbar,
            text="📷 Caméra : Arrêtée",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._cam_status.pack(side="right", padx=20)

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_face_detected(self, results: list[dict]) -> None:
        """Callback appelé quand un visage est détecté.

        Tente d'enregistrer la présence via ``AuthManager`` et
        affiche une notification toast.

        Args:
            results: Résultats de détection du FaceEngine.
        """
        for result in results:
            name = result.get("name", "Inconnu")
            confidence = result.get("confidence", 0.0)

            if name == "Inconnu":
                continue

            # Enregistrer la présence
            record = self._auth_manager.register_presence(name, confidence)

            if record is None:
                continue

            if record.get("already_checked_in"):
                # Cooldown actif — pas de notification
                continue

            # Afficher le toast
            status = record.get("status", "IN_TIME")
            time_str = record["time"].strftime("%H:%M:%S")

            class_num = record.get("class_number", "") or self._class_entry.get().strip()
            class_info = f" — Classe {class_num}" if class_num else ""

            if status == "IN_TIME":
                self._toast.show_success(
                    f"✅ {name}",
                    f"Arrivée à {time_str} — IN TIME{class_info}",
                )
            else:
                self._toast.show_warning(
                    f"🟡 {name}",
                    f"Arrivée à {time_str} — LATE{class_info}",
                )

            # Rafraîchir les données
            self._refresh_data()

    def _pause_live_camera(self) -> None:
        """Libère la webcam (enrôlement, analyse image, etc.)."""
        self._camera_was_running = self._camera.is_running()
        if self._camera_was_running:
            self._camera.stop()
            self._cam_btn.configure(
                text="📷 Démarrer Caméra",
                fg_color=COLORS["success"],
            )
            self._cam_status.configure(text="📷 Caméra : En pause")
            logger.info("Caméra principale mise en pause.")

    def _resume_live_camera(self) -> None:
        """Relance la webcam si elle tournait avant la pause."""
        if self._camera_was_running and not self._camera.is_running():
            self._camera.start()
            self._cam_btn.configure(
                text="⏹ Arrêter Caméra",
                fg_color=COLORS["warning"],
            )
            self._cam_status.configure(text="🔴 Caméra : En direct")
            logger.info("Caméra principale reprise.")

    def _toggle_camera(self) -> None:
        """Active/désactive le flux caméra."""
        if self._camera.is_running():
            self._camera.stop()
            self._cam_btn.configure(
                text="📷 Démarrer Caméra",
                fg_color=COLORS["success"],
            )
            self._cam_status.configure(text="📷 Caméra : Arrêtée")
        else:
            self._camera.start()
            self._cam_btn.configure(
                text="⏹ Arrêter Caméra",
                fg_color=COLORS["warning"],
            )
            self._cam_status.configure(text="🔴 Caméra : En direct")

    def _on_class_changed(self, _event=None) -> None:
        """Met à jour le numéro de classe pour les prochains pointages."""
        class_number = self._class_entry.get().strip()
        self._auth_manager.set_class_number(class_number)
        self._status_text.configure(
            text=f"Classe active : {class_number or '(non définie)'}",
        )

    def _auto_start_camera(self) -> None:
        """Démarre automatiquement la webcam pour la détection en direct."""
        if not self._camera.is_running():
            self._toggle_camera()

    def _open_photo_upload(self) -> None:
        """Ouvre l'interface d'upload de photos pour le gestionnaire."""
        self._pause_live_camera()

        def on_close() -> None:
            self._resume_live_camera()

        PhotoUploadUI(
            self,
            enrollment_manager=self._enrollment_manager,
            face_engine=self._face_engine,
            on_success=self._on_photos_uploaded,
            on_close=on_close,
        )

    def _on_photos_uploaded(self) -> None:
        """Rafraîchit l'UI après un upload de photos réussi."""
        self._stat_cards["employees"].update_value(
            str(self._face_engine.employee_count)
        )
        self._toast.show_success(
            "📤 Photos enregistrées",
            "Le visage est disponible pour la reconnaissance.",
        )

    def _open_enrollment(self) -> None:
        """Ouvre la fenêtre d'enrôlement."""
        self._pause_live_camera()

        def on_close() -> None:
            self._resume_live_camera()

        EnrollmentUI(
            self,
            self._enrollment_manager,
            on_close=on_close,
        )

    def _export_excel(self) -> None:
        """Exporte les présences du jour en Excel."""
        try:
            filepath = self._exporter.export_today()
            self._toast.show_success(
                "📊 Export réussi",
                f"Fichier : {os.path.basename(filepath)}",
            )
            self._status_text.configure(
                text=f"✅ Export : {os.path.basename(filepath)}",
            )
            logger.info("Export Excel : %s", filepath)
        except Exception as e:
            self._toast.show_warning("❌ Erreur export", str(e))
            logger.error("Erreur export Excel : %s", e)

    def _analyze_photo(self) -> None:
        """Analyse une image importée (sans bloquer la caméra)."""
        if cv2 is None:
            self._toast.show_warning(
                "❌ Analyse impossible",
                "OpenCV (cv2) n'est pas disponible.",
            )
            return

        filepath = filedialog.askopenfilename(
            parent=self,
            title="Sélectionner une photo à analyser",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.bmp"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not filepath:
            return

        self._pause_live_camera()
        self._status_text.configure(text="🖼️ Analyse de l'image en cours…")
        self._toast.show_success(
            "Analyse",
            "Traitement en cours — la webcam reprendra après.",
        )

        thread = threading.Thread(
            target=self._run_analyze_photo,
            args=(filepath,),
            daemon=True,
        )
        thread.start()

    def _run_analyze_photo(self, filepath: str) -> None:
        """Analyse IA dans un thread (évite le gel de l'interface)."""
        try:
            frame = cv2.imread(filepath)
            if frame is None:
                raise ValueError("Image non lisible (format non supporté).")

            results = self._face_engine.detect_and_identify(
                frame, apply_frame_skip=False
            )
            self.after(0, lambda: self._finish_analyze_photo(filepath, results, None))
        except Exception as e:
            logger.error("Erreur analyse photo : %s", e)
            self.after(0, lambda: self._finish_analyze_photo(filepath, None, e))

    def _finish_analyze_photo(
        self,
        filepath: str,
        results: Optional[list],
        error: Optional[Exception],
    ) -> None:
        """Affiche le résultat et relance la webcam."""
        try:
            if error is not None:
                self._toast.show_warning("❌ Erreur analyse", str(error))
                return
            if not results:
                self._toast.show_warning(
                    "Aucun visage",
                    "Aucun visage détecté sur cette image.",
                )
                return
            self._on_face_detected(results)
            self._status_text.configure(
                text=f"🖼️ Analyse image : {os.path.basename(filepath)}"
            )
        finally:
            self._resume_live_camera()

    # ------------------------------------------------------------------
    # Data Refresh
    # ------------------------------------------------------------------

    def _refresh_data(self) -> None:
        """Rafraîchit l'historique et les statistiques."""
        try:
            # Historique
            records = self._db.get_today_attendance()
            self._history.load_records(records)

            # Statistiques
            stats = self._db.get_stats_today()
            self._stat_cards["total"].update_value(str(stats["total"]))
            self._stat_cards["in_time"].update_value(str(stats["in_time"]))
            self._stat_cards["late"].update_value(str(stats["late"]))
            self._stat_cards["employees"].update_value(
                str(self._face_engine.employee_count)
            )

        except Exception as e:
            logger.error("Erreur rafraîchissement données : %s", e)

    def _schedule_refresh(self) -> None:
        """Programme un rafraîchissement toutes les 10 secondes."""
        self._refresh_data()
        self.after(10000, self._schedule_refresh)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------

    def _update_clock(self) -> None:
        """Met à jour l'horloge dans la top bar."""
        now = datetime.now()
        days_fr = [
            "Lundi", "Mardi", "Mercredi", "Jeudi",
            "Vendredi", "Samedi", "Dimanche",
        ]
        months_fr = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ]

        day_name = days_fr[now.weekday()]
        month_name = months_fr[now.month]
        date_str = f"📅 {day_name} {now.day} {month_name} {now.year}"
        time_str = f"🕐 {now.strftime('%H:%M:%S')}"

        self._datetime_label.configure(text=f"{date_str}   {time_str}")
        self.after(1000, self._update_clock)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_closing(self) -> None:
        """Nettoyage avant fermeture de l'application."""
        logger.info("Fermeture de l'application…")
        self._camera.stop()
        self._db.close()
        self.destroy()

    def run(self) -> None:
        """Lance la boucle principale de l'application."""
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger.info("Application démarrée.")
        self.mainloop()
