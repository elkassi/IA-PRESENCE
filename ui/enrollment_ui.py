"""
Enrollment UI — Interface graphique pour l'enrôlement des employés.
"""

import logging
import queue
import threading
from typing import Callable, Optional

import customtkinter as ctk
from tkinter import filedialog

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import COLORS, PHOTOS_MIN_ENROLLMENT
from core.enrollment import EnrollmentManager

logger = logging.getLogger(__name__)


class EnrollmentUI(ctk.CTkToplevel):
    """Fenêtre d'enrôlement d'un nouvel employé."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        enrollment_manager: EnrollmentManager,
        on_close: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._enrollment_manager = enrollment_manager
        self._on_close = on_close
        self._is_running = False
        self._selected_photos: list[str] = []
        self._ui_queue: queue.Queue = queue.Queue()

        self.title("➕ Enrôlement — Nouvel Employé")
        self.geometry("540x620")
        self.minsize(500, 560)
        self.resizable(True, True)
        self.configure(fg_color=COLORS["bg_primary"])
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._poll_ui_queue()
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        logger.info("EnrollmentUI ouverte.")

    def _build_ui(self) -> None:
        """Construit l'interface."""
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        container.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            container,
            text="👤 Enrôlement d'un Nouvel Employé",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(pady=(8, 4))

        self._subtitle = ctk.CTkLabel(
            container,
            text=f"Mode webcam : {PHOTOS_MIN_ENROLLMENT} photos (caméra libérée)",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
            wraplength=480,
        )
        self._subtitle.pack(pady=(0, 12))

        # Mode
        mode_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        mode_frame.pack(padx=16, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            mode_frame,
            text="Mode d'enrôlement :",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(padx=16, pady=(12, 6), anchor="w")

        self._mode_var = ctk.StringVar(value="Importer photos")
        ctk.CTkOptionMenu(
            mode_frame,
            values=["Importer photos", "Webcam"],
            variable=self._mode_var,
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_secondary"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["border"],
            command=self._on_mode_changed,
        ).pack(padx=16, pady=(0, 12), fill="x")

        # Formulaire nom / département
        form_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        form_frame.pack(padx=16, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            form_frame,
            text="Nom complet :",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(padx=16, pady=(12, 5), anchor="w")

        self._name_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ex: Noureddine EL Kassi",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )
        self._name_entry.pack(padx=16, fill="x")

        ctk.CTkLabel(
            form_frame,
            text="Département (optionnel) :",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(padx=16, pady=(10, 5), anchor="w")

        self._dept_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ex: Informatique",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )
        self._dept_entry.pack(padx=16, pady=(0, 12), fill="x")

        # Import photos (visible par défaut)
        self._import_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["accent"],
            corner_radius=15,
        )
        self._import_frame.pack(padx=16, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            self._import_frame,
            text="📁 Étape 1 — Choisir les photos sur votre PC",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(padx=16, pady=(14, 8))

        ctk.CTkButton(
            self._import_frame,
            text="📂 OUVrir l'explorateur de fichiers",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=48,
            fg_color=COLORS["bg_primary"],
            hover_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            corner_radius=12,
            command=self._select_photos,
        ).pack(padx=16, pady=(0, 8), fill="x")

        self._photo_count_label = ctk.CTkLabel(
            self._import_frame,
            text="Aucune photo sélectionnée.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._photo_count_label.pack(padx=16, pady=(0, 14), anchor="w")

        # Bouton démarrer (bien visible)
        self._start_btn = ctk.CTkButton(
            container,
            text="✅ ENREGISTRER (étape 2)",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=12,
            command=self._start_enrollment,
        )
        self._start_btn.pack(padx=16, pady=(0, 10), fill="x")

        ctk.CTkButton(
            container,
            text="Annuler",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=12,
            command=self._close_window,
        ).pack(padx=16, pady=(0, 10), fill="x")

        # Progression
        progress_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
        )
        progress_frame.pack(padx=16, pady=(0, 8), fill="x")

        self._progress_label = ctk.CTkLabel(
            progress_frame,
            text="Import : nom + photos + bouton ENREGISTRER",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            wraplength=460,
        )
        self._progress_label.pack(padx=16, pady=(12, 5))

        self._progress_bar = ctk.CTkProgressBar(
            progress_frame,
            progress_color=COLORS["accent"],
            fg_color=COLORS["bg_tertiary"],
            height=12,
            corner_radius=6,
        )
        self._progress_bar.pack(padx=16, pady=(0, 12), fill="x")
        self._progress_bar.set(0)

        self._on_mode_changed(self._mode_var.get())
        self.bind("<Return>", lambda _e: self._start_enrollment())

    def _on_mode_changed(self, mode: str) -> None:
        """Adapte l'interface au mode choisi."""
        mode = (mode or "").strip()
        if mode == "Importer photos":
            self._subtitle.configure(
                text="Importez 1 photo ou plus (JPG/PNG) depuis votre ordinateur",
            )
            self._import_frame.pack(padx=16, pady=(0, 10), fill="x")
            self._start_btn.configure(text="✅ ENREGISTRER (étape 2)")
            self._progress_label.configure(
                text="1) Ouvrir l'explorateur  2) Choisir photos  3) ENREGISTRER",
            )
        else:
            self._subtitle.configure(
                text=(
                    f"Webcam : capture de {PHOTOS_MIN_ENROLLMENT} photos "
                    "(la caméra principale sera libérée)"
                ),
            )
            self._import_frame.pack_forget()
            self._start_btn.configure(text="🚀 DÉMARRER capture webcam")
            self._progress_label.configure(
                text=f"La capture prendra {PHOTOS_MIN_ENROLLMENT} photos automatiquement",
            )

    def _select_photos(self) -> None:
        """Ouvre le sélecteur de fichiers (compatible fenêtre modale)."""
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
                text=f"✅ {len(self._selected_photos)} photo(s) sélectionnée(s).",
                text_color=COLORS["success"],
            )
            self._progress_label.configure(
                text="Photos OK — cliquez sur « ENREGISTRER (étape 2) »",
                text_color=COLORS["success"],
            )
        else:
            self._photo_count_label.configure(
                text="Aucune photo — cliquez sur « Ouvrir l'explorateur »",
                text_color=COLORS["warning"],
            )

    def _start_enrollment(self) -> None:
        """Lance l'enrôlement dans un thread séparé."""
        name = self._name_entry.get().strip()
        department = self._dept_entry.get().strip()

        if not name:
            self._progress_label.configure(
                text="⚠️ Saisissez un nom.",
                text_color=COLORS["warning"],
            )
            return

        mode = self._mode_var.get().strip()
        if mode == "Importer photos" and not self._selected_photos:
            self._progress_label.configure(
                text="⚠️ Cliquez d'abord sur « Ouvrir l'explorateur de fichiers »",
                text_color=COLORS["warning"],
            )
            return

        if self._is_running:
            return

        self._is_running = True
        self._start_btn.configure(state="disabled", text="⏳ En cours…")
        self._name_entry.configure(state="disabled")
        self._dept_entry.configure(state="disabled")
        self._progress_bar.set(0.05)
        self._progress_label.configure(
            text="⏳ Traitement — ne fermez pas cette fenêtre…",
            text_color=COLORS["text_primary"],
        )
        self.update_idletasks()

        thread = threading.Thread(
            target=self._run_enrollment,
            args=(name, department, mode, list(self._selected_photos)),
            daemon=True,
        )
        thread.start()

    def _run_enrollment(
        self, name: str, department: str, mode: str, selected_photos: list[str]
    ) -> None:
        """Exécute l'enrôlement (thread secondaire)."""
        try:
            if mode == "Importer photos":
                success = self._enrollment_manager.start_enrollment_from_photos(
                    employee_name=name,
                    department=department,
                    photo_paths=selected_photos,
                    progress_callback=self._update_progress_safe,
                    min_photos_required=1,
                )
            else:
                success = self._enrollment_manager.start_enrollment(
                    employee_name=name,
                    department=department,
                    progress_callback=self._update_progress_safe,
                )

            if success:
                self._update_ui_safe("✅ Enrôlement réussi !", COLORS["success"], 1.0)
            else:
                self._update_ui_safe("❌ Enrôlement échoué.", COLORS["warning"], 0.0)
        except Exception as e:
            logger.error("Erreur enrôlement : %s", e)
            self._update_ui_safe(f"❌ Erreur : {e}", COLORS["warning"], 0.0)
        finally:
            self._is_running = False
            self._reenable_form()

    def _close_window(self) -> None:
        """Ferme la fenêtre et notifie le parent."""
        if self._on_close:
            try:
                self._on_close()
            except Exception:
                pass
        self.destroy()

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                task = self._ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(50, self._poll_ui_queue)

    def _run_on_ui_thread(self, func) -> None:
        self._ui_queue.put(func)

    def _update_progress_safe(self, current: int, total: int, message: str) -> None:
        progress = min(1.0, current / max(total, 1))

        def update() -> None:
            self._progress_bar.set(max(progress, 0.05))
            self._progress_label.configure(
                text=message,
                text_color=COLORS["text_primary"],
            )

        self._run_on_ui_thread(update)

    def _update_ui_safe(self, message: str, color: str, progress: float) -> None:
        def update() -> None:
            self._progress_bar.set(progress)
            self._progress_label.configure(text=message, text_color=color)

        self._run_on_ui_thread(update)

    def _reenable_form(self) -> None:
        mode = self._mode_var.get().strip()
        label = (
            "✅ ENREGISTRER (étape 2)"
            if mode == "Importer photos"
            else "🚀 DÉMARRER capture webcam"
        )

        def update() -> None:
            self._start_btn.configure(state="normal", text=label)
            self._name_entry.configure(state="normal")
            self._dept_entry.configure(state="normal")

        self._run_on_ui_thread(update)
