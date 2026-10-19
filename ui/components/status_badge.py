"""
Status Badge — Badge arrondi coloré pour IN TIME / LATE.

Affiche un label avec un fond vert (IN_TIME) ou orange (LATE)
dans un coin arrondi, utilisable dans les listes de présence.
"""

import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import COLORS


class StatusBadge(ctk.CTkFrame):
    """Badge de statut arrondi et coloré.

    Attributes:
        _label: Label interne affichant le texte du statut.
    """

    STATUS_CONFIG = {
        "IN_TIME": {
            "text": "✅ IN TIME",
            "fg_color": COLORS["success"],
            "text_color": "#ffffff",
        },
        "LATE": {
            "text": "🟡 LATE",
            "fg_color": COLORS["warning"],
            "text_color": "#ffffff",
        },
    }

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        status: str = "IN_TIME",
        **kwargs,
    ) -> None:
        """Initialise le badge.

        Args:
            master: Widget parent.
            status: ``'IN_TIME'`` ou ``'LATE'``.
        """
        config = self.STATUS_CONFIG.get(status, self.STATUS_CONFIG["IN_TIME"])

        super().__init__(
            master,
            fg_color=config["fg_color"],
            corner_radius=12,
            height=28,
            **kwargs,
        )

        self._label = ctk.CTkLabel(
            self,
            text=config["text"],
            text_color=config["text_color"],
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=10,
            pady=2,
        )
        self._label.pack(expand=True, fill="both", padx=4, pady=2)

    def update_status(self, status: str) -> None:
        """Met à jour le statut affiché.

        Args:
            status: ``'IN_TIME'`` ou ``'LATE'``.
        """
        config = self.STATUS_CONFIG.get(status, self.STATUS_CONFIG["IN_TIME"])
        self.configure(fg_color=config["fg_color"])
        self._label.configure(
            text=config["text"],
            text_color=config["text_color"],
        )
