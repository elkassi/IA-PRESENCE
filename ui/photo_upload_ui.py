"""
Photo Upload UI — Interface gestionnaire pour enregistrer des visages.

Permet d'importer une ou plusieurs photos avec le nom de la personne.
Les images sont copiées localement, un embedding est généré et chargé
automatiquement dans le moteur de reconnaissance faciale.
"""

import logging
import queue
import threading

import customtkinter as ctk
from tkinter import filedialog

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import COLORS
from core.enrollment import EnrollmentManager
from core.face_engine import FaceEngine

logger = logging.getLogger(__name__)


class PhotoUploadUI(ctk.CTkToplevel):
    """Fenêtre d'upload de photos pour la reconnaissance faciale.

    Attributes:
        _enrollment_manager: Gestionnaire d'enrôlement.
        _face_engine: Moteur IA (rechargement après upload).
        _on_success: Callback optionnel après enrôlement réussi.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        enrollment_manager: EnrollmentManager,
        face_engine: FaceEngine,
        on_success=None,
        on_close=None,
        **kwargs,
    ) -> None:
        """Initialise la fenêtre d'upload.

        Args:
            master: Fenêtre parente.
            enrollment_manager: Instance ``EnrollmentManager``.
            face_engine: Instance ``FaceEngine``.
            on_success: Callable sans argument après succès.
        """
        super().__init__(master, **kwargs)

        self._enrollment_manager = enrollment_manager
        self._face_engine = face_engine
        self._on_success = on_success
        self._on_close = on_close
        self._is_running = False
        self._selected_photos: list[str] = []
        self._ui_queue: queue.Queue = queue.Queue()

        self.title("📤 Ajouter des photos — Reconnaissance faciale")
        self.geometry("520x580")
        self.minsize(480, 520)
        self.resizable(True, True)
        self.configure(fg_color=COLORS["bg_primary"])
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._poll_ui_queue()
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        logger.info("PhotoUploadUI ouverte.")

    def _build_ui(self) -> None:
        """Construit l'interface."""
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        container.pack(fill="both", expand=True, padx=10, pady=10)

        title = ctk.CTkLabel(
            container,
            text="📤 Enregistrer un visage",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.pack(pady=(10, 5))

        subtitle = ctk.CTkLabel(
            container,
            text="Importez des photos avec le nom de la personne (label)",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        )
        subtitle.pack(pady=(0, 12))

        form = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        form.pack(padx=20, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            form,
            text="Nom de la personne :",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(padx=20, pady=(15, 5), anchor="w")

        self._name_entry = ctk.CTkEntry(
            form,
            placeholder_text="Ex: Marie Dupont",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )
        self._name_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(
            form,
            text="Département (optionnel) :",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(padx=20, pady=(10, 5), anchor="w")

        self._dept_entry = ctk.CTkEntry(
            form,
            placeholder_text="Ex: Génie informatique",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )
        self._dept_entry.pack(padx=20, pady=(0, 15), fill="x")

        photos_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        photos_frame.pack(padx=20, pady=(0, 10), fill="x")

        ctk.CTkButton(
            photos_frame,
            text="📁 Choisir des photos…",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=12,
            command=self._select_photos,
        ).pack(padx=20, pady=(15, 8), fill="x")

        self._photo_count_label = ctk.CTkLabel(
            photos_frame,
            text="Aucune photo sélectionnée.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._photo_count_label.pack(padx=20, pady=(0, 12), anchor="w")

        # Boutons d'action (placés avant la progression pour rester visibles)
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=(0, 10), fill="x", padx=20)

        self._upload_btn = ctk.CTkButton(
            btn_frame,
            text="✅ ENREGISTRER",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=12,
            command=self._start_upload,
        )
        self._upload_btn.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Fermer",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=12,
            command=self._close_window,
        ).pack(fill="x")

        progress_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        progress_frame.pack(padx=20, pady=(0, 10), fill="x")

        self._progress_label = ctk.CTkLabel(
            progress_frame,
            text="Étape 1 : nom + photos  →  Étape 2 : bouton ENREGISTRER ci-dessus",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            wraplength=440,
        )
        self._progress_label.pack(padx=20, pady=(12, 5))

        self._progress_bar = ctk.CTkProgressBar(
            progress_frame,
            progress_color=COLORS["accent"],
            fg_color=COLORS["bg_tertiary"],
            height=12,
            corner_radius=6,
        )
        self._progress_bar.pack(padx=20, pady=(0, 12), fill="x")
        self._progress_bar.set(0)

        self.bind("<Return>", lambda _e: self._start_upload())

    def _close_window(self) -> None:
        """Ferme la fenêtre et relance la webcam principale."""
        if self._on_close:
            try:
                self._on_close()
            except Exception:
                pass
        self.destroy()

    def _select_photos(self) -> None:
        """Ouvre le sélecteur de fichiers."""
        try:
            self.grab_release()
        except Exception:
            pass

        paths = filedialog.askopenfilenames(
            parent=self,
            title="Sélectionner des photos (Ctrl+clic pour plusieurs)",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.bmp"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("Tous les fichiers", "*.*"),
            ],
        )

        try:
            self.grab_set()
        except Exception:
            pass
        self._selected_photos = list(paths) if paths else []
        if self._selected_photos:
            self._photo_count_label.configure(
                text=f"✅ {len(self._selected_photos)} photo(s) prête(s).",
                text_color=COLORS["success"],
            )
            self._progress_label.configure(
                text="Photos prêtes — cliquez sur le bouton violet « ENREGISTRER »",
                text_color=COLORS["success"],
            )
        else:
            self._photo_count_label.configure(
                text="Aucune photo sélectionnée.",
                text_color=COLORS["text_muted"],
            )

    def _start_upload(self) -> None:
        """Lance l'enregistrement dans un thread."""
        name = self._name_entry.get().strip()
        department = self._dept_entry.get().strip()

        if not name:
            self._progress_label.configure(
                text="⚠️ Saisissez le nom de la personne.",
                text_color=COLORS["warning"],
            )
            return
        if not self._selected_photos:
            self._progress_label.configure(
                text="⚠️ Sélectionnez au moins une photo.",
                text_color=COLORS["warning"],
            )
            return
        if self._is_running:
            return

        self._is_running = True
        self._upload_btn.configure(state="disabled", text="⏳ Traitement…")
        self._name_entry.configure(state="disabled")
        self._dept_entry.configure(state="disabled")
        self._progress_bar.set(0.05)
        self._progress_label.configure(
            text="⏳ Démarrage — copie des photos puis analyse IA…",
            text_color=COLORS["text_primary"],
        )
        self.update_idletasks()

        thread = threading.Thread(
            target=self._run_upload,
            args=(name, department, list(self._selected_photos)),
            daemon=True,
        )
        thread.start()

    def _run_upload(self, name: str, department: str, photos: list[str]) -> None:
        """Exécute l'enrôlement par import de photos."""
        try:
            success = self._enrollment_manager.start_enrollment_from_photos(
                employee_name=name,
                department=department,
                photo_paths=photos,
                progress_callback=self._update_progress_safe,
                min_photos_required=1,
            )
            if success:
                self._face_engine.load_employee_embeddings()
                self._update_ui_safe(
                    f"✅ {name} enregistré — reconnaissance active.",
                    COLORS["success"],
                    1.0,
                )
                if self._on_success:
                    self.after(0, self._on_success)
            else:
                self._update_ui_safe(
                    "❌ Échec : vérifiez que les photos contiennent un visage.",
                    COLORS["warning"],
                    0.0,
                )
        except Exception as e:
            logger.error("Erreur upload photos : %s", e)
            self._update_ui_safe(f"❌ Erreur : {e}", COLORS["warning"], 0.0)
        finally:
            self._is_running = False
            self._reenable_form()

    def _poll_ui_queue(self) -> None:
        """Traite les mises à jour UI depuis le thread principal."""
        try:
            while True:
                task = self._ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(50, self._poll_ui_queue)

    def _run_on_ui_thread(self, func) -> None:
        """Planifie une action sur le thread Tkinter principal."""
        self._ui_queue.put(func)

    def _update_progress_safe(self, current: int, total: int, message: str) -> None:
        """Met à jour la barre de progression (thread-safe)."""
        progress = min(1.0, current / max(total, 1))

        def update() -> None:
            self._progress_bar.set(max(progress, 0.05))
            self._progress_label.configure(
                text=message,
                text_color=COLORS["text_primary"],
            )

        self._run_on_ui_thread(update)

    def _update_ui_safe(self, message: str, color: str, progress: float) -> None:
        """Met à jour le message final (thread-safe)."""

        def update() -> None:
            self._progress_bar.set(progress)
            self._progress_label.configure(text=message, text_color=color)

        self._run_on_ui_thread(update)

    def _reenable_form(self) -> None:
        """Réactive le formulaire après traitement."""

        def update() -> None:
            self._upload_btn.configure(state="normal", text="✅ ENREGISTRER")
            self._name_entry.configure(state="normal")
            self._dept_entry.configure(state="normal")

        self._run_on_ui_thread(update)
