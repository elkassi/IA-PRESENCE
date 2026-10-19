"""
Tests — AuthManager.

Teste la logique de pointage : statut IN_TIME/LATE, cooldown
anti-doublons, et enregistrement de présence.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)

from core.auth_manager import AuthManager


class TestAuthManager:
    """Tests pour AuthManager."""

    @pytest.fixture
    def auth_manager(self, db_manager):
        """Fournit une instance AuthManager."""
        return AuthManager(db_manager)

    def test_get_status_in_time(self, auth_manager):
        """Arrivée avant 08:30 → IN_TIME."""
        arrival = datetime(2026, 5, 19, 8, 0, 0)
        assert auth_manager.get_status(arrival) == "IN_TIME"

    def test_get_status_at_limit(self, auth_manager):
        """Arrivée à 08:30 exactement → IN_TIME."""
        arrival = datetime(2026, 5, 19, 8, 30, 0)
        assert auth_manager.get_status(arrival) == "IN_TIME"

    def test_get_status_late(self, auth_manager):
        """Arrivée après 08:30 → LATE."""
        arrival = datetime(2026, 5, 19, 9, 15, 0)
        assert auth_manager.get_status(arrival) == "LATE"

    def test_can_checkin_first_time(self, auth_manager, sample_employee):
        """Premier pointage autorisé."""
        assert auth_manager.can_checkin(sample_employee["name"]) is True

    def test_can_checkin_after_cooldown(self, auth_manager, db_manager, sample_employee):
        """Pointage autorisé après le cooldown."""
        # Simuler un pointage il y a 31 minutes
        old_time = datetime.now() - timedelta(minutes=31)
        with patch.object(db_manager, 'get_last_checkin', return_value=old_time):
            assert auth_manager.can_checkin(sample_employee["name"]) is True

    def test_can_checkin_during_cooldown(self, auth_manager, db_manager, sample_employee):
        """Pointage refusé pendant le cooldown."""
        # Simuler un pointage il y a 10 minutes
        recent_time = datetime.now() - timedelta(minutes=10)
        with patch.object(db_manager, 'get_last_checkin', return_value=recent_time):
            assert auth_manager.can_checkin(sample_employee["name"]) is False

    def test_register_presence_success(self, auth_manager, sample_employee):
        """Enregistrement réussi retourne les infos."""
        result = auth_manager.register_presence(sample_employee["name"], 0.95)
        assert result is not None
        assert result["name"] == sample_employee["name"]
        assert result["status"] in ("IN_TIME", "LATE")
        assert result["already_checked_in"] is False

    def test_register_presence_unknown_employee(self, auth_manager):
        """Enregistrement d'un employé inconnu retourne None."""
        result = auth_manager.register_presence("Inconnu Total", 0.8)
        assert result is None

    def test_register_presence_cooldown_active(self, auth_manager, db_manager, sample_employee):
        """Double pointage dans le cooldown signale already_checked_in."""
        # Premier pointage
        auth_manager.register_presence(sample_employee["name"], 0.95)
        # Deuxième tentative
        result = auth_manager.register_presence(sample_employee["name"], 0.92)
        assert result is not None
        assert result["already_checked_in"] is True

    def test_register_presence_stores_class_number(self, db_manager, sample_employee):
        """Le numéro de classe est enregistré lors du pointage."""
        auth = AuthManager(db_manager, class_number="5")
        result = auth.register_presence(sample_employee["name"], 0.9)
        assert result is not None
        records = db_manager.get_today_attendance()
        assert records[0]["class_number"] == "5"

    def test_register_presence_has_time(self, auth_manager, sample_employee):
        """Le résultat contient un datetime."""
        result = auth_manager.register_presence(sample_employee["name"], 0.9)
        assert result is not None
        assert isinstance(result["time"], datetime)
