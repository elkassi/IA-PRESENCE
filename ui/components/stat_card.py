"""
Stat Card — Carte statistique réutilisable.

Affiche une icône, une valeur numérique et un label descriptif
dans un cadre arrondi avec fond sombre. Utilisée dans la barre
de statistiques du dashboard.
"""

import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import COLORS


class StatCard(ctk.CTkFrame):
    """Carte statistique avec icône, valeur et label.

    Attributes:
        _icon_label: Label affichant l'icône emoji.
        _value_label: Label affichant la valeur numérique.
        _text_label: Label affichant le texte descriptif.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        icon: str = "📊",
        value: str = "0",
        label: str = "Statistique",
        accent_color: str | None = None,
        **kwargs,
    ) -> None:
        """Initialise la carte statistique.

        Args:
            master: Widget parent.
            icon: Emoji ou texte pour l'icône.
            value: Valeur numérique à afficher.
            label: Texte descriptif sous la valeur.
            accent_color: Couleur d'accent pour la valeur.
        """
        super().__init__(
            master,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )

        color = accent_color or COLORS["accent"]

        # Icône
        self._icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=28),
            text_color=COLORS["text_primary"],
        )
        self._icon_label.pack(pady=(15, 5))

        # Valeur
        self._value_label = ctk.CTkLabel(
            self,
            text=str(value),
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=color,
        )
        self._value_label.pack(pady=(0, 2))

        # Label descriptif
        self._text_label = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        )
        self._text_label.pack(pady=(0, 15))

    def update_value(self, value: str) -> None:
        """Met à jour la valeur affichée.

        Args:
            value: Nouvelle valeur à afficher.
        """
        self._value_label.configure(text=str(value))

    def update_label(self, label: str) -> None:
        """Met à jour le label descriptif.

        Args:
            label: Nouveau texte descriptif.
        """
        self._text_label.configure(text=label)
