"""
Auth Manager — Gère la logique de pointage, statuts et anti-doublons.

Règles métier :
    - **IN TIME** : arrivée avant ``HEURE_LIMITE`` (configurable).
    - **LATE**    : arrivée après ``HEURE_LIMITE``.
    - **Anti-doublon** : un employé ne peut pointer qu'une fois par
      ``COOLDOWN_MINUTES`` (30 min par défaut).
"""

import logging
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import HEURE_LIMITE, COOLDOWN_MINUTES
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestionnaire d'authentification et de pointage.

    Attributes:
        _db: Instance du gestionnaire de base de données.
        _heure_limite: Heure limite pour le statut IN_TIME.
        _cooldown: Durée du cooldown anti-doublons en minutes.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        class_number: str = "",
    ) -> None:
        """Initialise avec accès à la base de données.

        Args:
            db_manager: Instance de ``DatabaseManager``.
            class_number: Numéro de classe courant pour les pointages.
        """
        self._db = db_manager
        self._heure_limite = HEURE_LIMITE
        self._cooldown = COOLDOWN_MINUTES
        self._class_number = class_number
        logger.info(
            "AuthManager initialisé (limite=%s, cooldown=%d min, classe=%s).",
            self._heure_limite, self._cooldown, self._class_number,
        )

    def set_class_number(self, class_number: str) -> None:
        """Met à jour le numéro de classe utilisé pour les pointages.

        Args:
            class_number: Numéro de classe (ex. ``"3"``).
        """
        self._class_number = (class_number or "").strip()
        logger.info("Numéro de classe mis à jour : %s", self._class_number)

    def can_checkin(self, employee_name: str) -> bool:
        """Vérifie si l'employé peut pointer (cooldown 30 min respecté).

        Args:
            employee_name: Nom de l'employé.

        Returns:
            ``True`` si le cooldown est respecté, ``False`` sinon.
        """
        last_checkin = self._db.get_last_checkin(employee_name)

        if last_checkin is None:
            logger.info("Premier pointage de '%s'.", employee_name)
            return True

        elapsed = datetime.now() - last_checkin
        cooldown_delta = timedelta(minutes=self._cooldown)

        if elapsed >= cooldown_delta:
            logger.info(
                "'%s' peut pointer (dernier pointage il y a %s).",
                employee_name, elapsed,
            )
            return True
        else:
            remaining = cooldown_delta - elapsed
            logger.info(
                "'%s' ne peut pas pointer (cooldown restant : %s).",
                employee_name, remaining,
            )
            return False

    def get_status(self, arrival_time: datetime) -> str:
        """Retourne le statut de présence selon l'heure d'arrivée.

        Args:
            arrival_time: Heure d'arrivée de l'employé.

        Returns:
            ``'IN_TIME'`` si avant l'heure limite, ``'LATE'`` sinon.
        """
        heure, minute = map(int, self._heure_limite.split(":"))
        limite = arrival_time.replace(hour=heure, minute=minute, second=0, microsecond=0)

        if arrival_time <= limite:
            return "IN_TIME"
        else:
            return "LATE"

    def register_presence(
        self, employee_name: str, confidence: float
    ) -> dict | None:
        """Enregistre une présence si toutes les conditions sont remplies.

        Vérifie :
            1. L'employé existe en base.
            2. Le cooldown est respecté.
            3. Le statut est calculé selon l'heure.

        Args:
            employee_name: Nom de l'employé reconnu.
            confidence: Score de confiance de la reconnaissance.

        Returns:
            Dict ``{name, status, time, already_checked_in}`` ou ``None``
            si refus (cooldown non respecté ou employé inconnu).
        """
        # Vérifier si l'employé existe
        employee = self._db.get_employee_by_name(employee_name)
        if employee is None:
            logger.warning("Employé '%s' non trouvé en base.", employee_name)
            return None

        # Vérifier le cooldown
        if not self.can_checkin(employee_name):
            logger.info("Pointage refusé pour '%s' (cooldown).", employee_name)
            return {
                "name": employee_name,
                "status": None,
                "time": datetime.now(),
                "already_checked_in": True,
            }

        # Calculer le statut
        now = datetime.now()
        status = self.get_status(now)

        # Enregistrer en base
        try:
            self._db.add_attendance_record(
                employee_id=employee["id"],
                status=status,
                confidence=confidence,
                class_number=self._class_number,
            )
            logger.info(
                "Présence enregistrée : %s — %s à %s (classe=%s, confiance=%.2f).",
                employee_name,
                status,
                now.strftime("%H:%M:%S"),
                self._class_number,
                confidence,
            )
            return {
                "name": employee_name,
                "status": status,
                "time": now,
                "class_number": self._class_number,
                "already_checked_in": False,
            }
        except Exception as e:
            logger.error(
                "Erreur lors de l'enregistrement de '%s' : %s",
                employee_name, e,
            )
            return None
