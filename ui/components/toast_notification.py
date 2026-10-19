"""
Toast Notification — Notification animée temporaire.

Apparaît en bas à droite de la fenêtre pendant 3 secondes lorsqu'un
employé est reconnu par le système. Animation de slide-in et fade-out.
"""

import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import COLORS


class ToastNotification(ctk.CTkFrame):
    """Notification toast animée qui apparaît et disparaît.

    Attributes:
        _title_label: Label du titre de la notification.
        _message_label: Label du message.
        _auto_destroy_id: ID du callback after() pour auto-destruction.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str = "Notification",
        message: str = "",
        duration_ms: int = 3000,
        toast_type: str = "success",
        **kwargs,
    ) -> None:
        """Initialise et affiche la notification toast.

        Args:
            master: Widget parent (fenêtre principale).
            title: Titre de la notification.
            message: Message détaillé.
            duration_ms: Durée d'affichage en millisecondes.
            toast_type: Type ``'success'`` (vert) ou ``'warning'`` (orange).
        """
        accent = COLORS["success"] if toast_type == "success" else COLORS["warning"]

        super().__init__(
            master,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=2,
            border_color=accent,
            **kwargs,
        )

        # Barre d'accent latérale
        accent_bar = ctk.CTkFrame(
            self,
            fg_color=accent,
            width=4,
            corner_radius=0,
        )
        accent_bar.pack(side="left", fill="y", padx=(0, 10))

        # Contenu
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=(0, 15), pady=10)

        # Titre
        self._title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self._title_label.pack(anchor="w")

        # Message
        if message:
            self._message_label = ctk.CTkLabel(
                content_frame,
                text=message,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            self._message_label.pack(anchor="w", pady=(2, 0))

        # Bouton fermer
        close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=14),
            command=self._dismiss,
        )
        close_btn.pack(side="right", padx=(0, 5), pady=5)

        # Positionnement en bas à droite
        self.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.lift()

        # Auto-destruction après la durée
        self._auto_destroy_id = self.after(duration_ms, self._dismiss)

    def _dismiss(self) -> None:
        """Fait disparaître la notification."""
        try:
            if self._auto_destroy_id:
                self.after_cancel(self._auto_destroy_id)
                self._auto_destroy_id = None
            self.destroy()
        except Exception:
            pass


class ToastManager:
    """Gestionnaire de notifications toast empilées.

    Gère l'affichage séquentiel des notifications pour éviter
    les superpositions.

    Attributes:
        _master: Fenêtre parent.
        _active_toasts: Liste des toasts actifs.
    """

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Initialise le gestionnaire.

        Args:
            master: Fenêtre parent pour les toasts.
        """
        self._master = master
        self._active_toasts: list[ToastNotification] = []

    def show_success(self, title: str, message: str = "") -> None:
        """Affiche un toast de succès (vert).

        Args:
            title: Titre de la notification.
            message: Message détaillé.
        """
        self._show(title, message, "success")

    def show_warning(self, title: str, message: str = "") -> None:
        """Affiche un toast d'avertissement (orange).

        Args:
            title: Titre de la notification.
            message: Message détaillé.
        """
        self._show(title, message, "warning")

    def _show(self, title: str, message: str, toast_type: str) -> None:
        """Affiche un toast et gère l'empilement.

        Args:
            title: Titre de la notification.
            message: Message détaillé.
            toast_type: Type de notification.
        """
        # Nettoyer les toasts détruits
        self._active_toasts = [t for t in self._active_toasts if t.winfo_exists()]

        toast = ToastNotification(
            self._master,
            title=title,
            message=message,
            toast_type=toast_type,
        )

        # Décaler les toasts existants vers le haut
        offset = len(self._active_toasts) * 80
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20 - offset)

        self._active_toasts.append(toast)
