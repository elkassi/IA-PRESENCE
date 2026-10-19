"""
Tests — DatabaseManager.

Teste les opérations CRUD sur les tables employees et attendance_records,
les statistiques, la sauvegarde et la vérification d'intégrité.
"""

import os
import sys
from datetime import datetime

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)


class TestDatabaseManager:
    """Tests pour DatabaseManager."""

    def test_create_tables(self, db_manager):
        """Les tables sont créées automatiquement à l'initialisation."""
        # Les tables existent si on peut exécuter des requêtes
        employees = db_manager.get_all_employees()
        assert isinstance(employees, list)

    def test_add_employee(self, db_manager):
        """Ajout d'un employé retourne un ID valide."""
        emp_id = db_manager.add_employee("Alice Dupont", "RH")
        assert emp_id > 0

    def test_add_employee_duplicate(self, db_manager):
        """Ajout d'un employé avec un nom existant lève une erreur."""
        db_manager.add_employee("Bob Martin", "IT")
        with pytest.raises(Exception):
            db_manager.add_employee("Bob Martin", "Finance")

    def test_get_employee_by_name(self, db_manager):
        """Recherche d'un employé par nom retourne ses infos."""
        db_manager.add_employee("Charlie Test", "Dev")
        employee = db_manager.get_employee_by_name("Charlie Test")
        assert employee is not None
        assert employee["name"] == "Charlie Test"
        assert employee["department"] == "Dev"

    def test_get_employee_not_found(self, db_manager):
        """Recherche d'un employé inexistant retourne None."""
        result = db_manager.get_employee_by_name("Fantôme")
        assert result is None

    def test_get_all_employees(self, db_manager):
        """Liste de tous les employés actifs."""
        db_manager.add_employee("Emp1", "A")
        db_manager.add_employee("Emp2", "B")
        employees = db_manager.get_all_employees()
        assert len(employees) == 2

    def test_add_attendance_record(self, db_manager, sample_employee):
        """Ajout d'un enregistrement de présence."""
        record_id = db_manager.add_attendance_record(
            employee_id=sample_employee["id"],
            status="IN_TIME",
            confidence=0.95,
        )
        assert record_id > 0

    def test_add_attendance_record_with_class(self, db_manager, sample_employee):
        """Le numéro de classe est enregistré avec la présence."""
        db_manager.add_attendance_record(
            employee_id=sample_employee["id"],
            status="IN_TIME",
            confidence=0.95,
            class_number="3A",
        )
        records = db_manager.get_today_attendance()
        assert len(records) == 1
        assert records[0]["class_number"] == "3A"

    def test_get_last_checkin(self, db_manager, sample_employee):
        """Dernier pointage retourne un datetime."""
        db_manager.add_attendance_record(
            employee_id=sample_employee["id"],
            status="IN_TIME",
            confidence=0.9,
        )
        last = db_manager.get_last_checkin(sample_employee["name"])
        assert last is not None
        assert isinstance(last, datetime)

    def test_get_last_checkin_no_record(self, db_manager):
        """Dernier pointage d'un employé sans pointage retourne None."""
        db_manager.add_employee("NoCheckin User", "Test")
        last = db_manager.get_last_checkin("NoCheckin User")
        assert last is None

    def test_get_today_attendance(self, db_manager, sample_employee):
        """Présences du jour retourne les enregistrements."""
        db_manager.add_attendance_record(
            employee_id=sample_employee["id"],
            status="IN_TIME",
            confidence=0.88,
        )
        records = db_manager.get_today_attendance()
        assert len(records) == 1
        assert records[0]["name"] == sample_employee["name"]
        assert records[0]["status"] == "IN_TIME"

    def test_get_stats_today(self, db_manager, sample_employee):
        """Statistiques du jour correctes."""
        db_manager.add_attendance_record(
            employee_id=sample_employee["id"],
            status="IN_TIME",
            confidence=0.9,
        )
        emp2_id = db_manager.add_employee("Late User", "Test")
        db_manager.add_attendance_record(
            employee_id=emp2_id,
            status="LATE",
            confidence=0.85,
        )

        stats = db_manager.get_stats_today()
        assert stats["total"] == 2
        assert stats["in_time"] == 1
        assert stats["late"] == 1

    def test_verify_integrity(self, db_manager):
        """La base est intègre après création."""
        assert db_manager.verify_integrity() is True

    def test_backup_database(self, db_manager):
        """La sauvegarde crée un fichier."""
        backup_path = db_manager.backup_database()
        assert os.path.exists(backup_path)
        assert "backup" in backup_path
