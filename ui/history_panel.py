"""
History Panel — Historique scrollable des présences.

Affiche la liste des pointages du jour (et historiques) avec le nom
de l'employé, l'heure d'arrivée et le badge de statut. Filtrable
par date.
"""

import logging
from datetime import datetime
from typing import Optional

import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import COLORS
from ui.components.status_badge import StatusBadge

logger = logging.getLogger(__name__)


class HistoryPanel(ctk.CTkFrame):
    """Panneau d'historique des présences.

    Attributes:
        _scroll_frame: Frame scrollable contenant les entrées.
        _title_label: Titre du panneau.
        _entries: Liste des widgets d'entrées affichées.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        **kwargs,
    ) -> None:
        """Initialise le panneau d'historique.

        Args:
            master: Widget parent.
        """
        super().__init__(
            master,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )

        self._entries: list[ctk.CTkFrame] = []
        self._build_ui()
        logger.info("HistoryPanel initialisé.")

    def _build_ui(self) -> None:
        """Construit l'interface du panneau."""
        # En-tête
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        self._title_label = ctk.CTkLabel(
            header,
            text="📋 Présences du jour",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self._title_label.pack(side="left")

        # Compteur
        self._count_label = ctk.CTkLabel(
            header,
            text="0",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_muted"],
        )
        self._count_label.pack(side="right")

        # Séparateur
        sep = ctk.CTkFrame(self, fg_color=COLORS["border"], height=1)
        sep.pack(fill="x", padx=15, pady=(0, 5))

        # Frame scrollable
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def add_entry(
        self,
        name: str,
        time_str: str,
        status: str,
        confidence: float = 0.0,
        class_number: str = "",
    ) -> None:
        """Ajoute une entrée de présence au panneau.

        Args:
            name: Nom de l'employé.
            time_str: Heure d'arrivée formatée (HH:MM:SS).
            status: ``'IN_TIME'`` ou ``'LATE'``.
            confidence: Score de confiance.
            class_number: Numéro de classe du pointage.
        """
        entry = ctk.CTkFrame(
            self._scroll_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=10,
            height=55,
        )
        entry.pack(fill="x", pady=3, padx=5)
        entry.pack_propagate(False)

        # Icône
        icon = ctk.CTkLabel(
            entry,
            text="👤",
            font=ctk.CTkFont(size=20),
            width=35,
        )
        icon.pack(side="left", padx=(10, 5))

        # Nom
        name_label = ctk.CTkLabel(
            entry,
            text=name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        name_label.pack(side="left", padx=(0, 6), fill="x", expand=True)

        if class_number:
            class_label = ctk.CTkLabel(
                entry,
                text=f"Cl. {class_number}",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["accent"],
                width=50,
            )
            class_label.pack(side="left", padx=(0, 6))

        # Heure
        time_label = ctk.CTkLabel(
            entry,
            text=time_str,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        )
        time_label.pack(side="left", padx=(0, 10))

        # Badge statut
        badge = StatusBadge(entry, status=status)
        badge.pack(side="right", padx=(0, 10))

        self._entries.append(entry)
        self._count_label.configure(text=str(len(self._entries)))

    def clear(self) -> None:
        """Supprime toutes les entrées."""
        for entry in self._entries:
            entry.destroy()
        self._entries.clear()
        self._count_label.configure(text="0")

    def load_records(self, records: list[dict]) -> None:
        """Charge une liste d'enregistrements.

        Args:
            records: Liste de dicts ``{name, timestamp, status, confidence}``.
        """
        self.clear()
        for record in records:
            try:
                ts = datetime.fromisoformat(record["timestamp"])
                time_str = ts.strftime("%H:%M:%S")
            except (ValueError, TypeError, KeyError):
                time_str = "--:--:--"

            self.add_entry(
                name=record.get("name", "Inconnu"),
                time_str=time_str,
                status=record.get("status", "IN_TIME"),
                confidence=record.get("confidence", 0.0),
                class_number=record.get("class_number", "") or "",
            )

        logger.info("Historique chargé : %d enregistrements.", len(records))
