"""
DB Manager — Interface CRUD pour la base de données SQLite.

Gère toutes les opérations sur les tables ``employees`` et
``attendance_records`` : ajout, recherche, statistiques, sauvegarde
et vérification d'intégrité.

Schéma :
    employees(id, name, department, enrolled_at, active)
    attendance_records(id, employee_id, timestamp, date, status, confidence)
"""

import os
import shutil
import sqlite3
import logging
from datetime import datetime, date
from typing import Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DB_PATH
from database.models import (
    CREATE_EMPLOYEES_TABLE,
    CREATE_ATTENDANCE_TABLE,
    CREATE_INDEXES,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestionnaire SQLite pour IA-PRESENCE.

    Attributes:
        db_path: Chemin vers le fichier de base de données SQLite.
        _conn: Connexion SQLite active.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialise la connexion et crée les tables si nécessaire.

        Args:
            db_path: Chemin vers la base. Par défaut ``config.DB_PATH``.
        """
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.create_tables()
        self._migrate_schema()
        logger.info("DatabaseManager initialisé (%s).", self.db_path)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        """Crée les tables et index s'ils n'existent pas."""
        cursor = self._conn.cursor()
        cursor.execute(CREATE_EMPLOYEES_TABLE)
        cursor.execute(CREATE_ATTENDANCE_TABLE)
        cursor.executescript(CREATE_INDEXES)
        self._conn.commit()
        logger.info("Tables et index créés / vérifiés.")

    def _migrate_schema(self) -> None:
        """Applique les migrations légères (colonnes ajoutées après coup)."""
        cursor = self._conn.cursor()
        cursor.execute("PRAGMA table_info(attendance_records)")
        columns = {row[1] for row in cursor.fetchall()}
        if "class_number" not in columns:
            cursor.execute(
                "ALTER TABLE attendance_records "
                "ADD COLUMN class_number TEXT DEFAULT ''"
            )
            self._conn.commit()
            logger.info("Migration : colonne class_number ajoutée.")

    # ------------------------------------------------------------------
    # Employés
    # ------------------------------------------------------------------

    def add_employee(self, name: str, department: str = "") -> int:
        """Ajoute un employé et retourne son ID.

        Args:
            name: Nom complet de l'employé (unique).
            department: Département (optionnel).

        Returns:
            ID de l'employé créé.

        Raises:
            sqlite3.IntegrityError: Si le nom existe déjà.
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT INTO employees (name, department, enrolled_at) VALUES (?, ?, ?)",
                (name, department, datetime.now().isoformat()),
            )
            self._conn.commit()
            employee_id = cursor.lastrowid
            logger.info("Employé ajouté : %s (ID=%d).", name, employee_id)
            return employee_id
        except sqlite3.IntegrityError:
            logger.warning("L'employé '%s' existe déjà.", name)
            raise

    def get_employee_by_name(self, name: str) -> Optional[dict]:
        """Recherche un employé par nom.

        Args:
            name: Nom de l'employé.

        Returns:
            Dict avec les infos de l'employé ou ``None``.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE name = ? AND active = 1", (name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_employees(self) -> list[dict]:
        """Retourne la liste de tous les employés actifs.

        Returns:
            Liste de dicts avec les infos des employés.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE active = 1 ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Présences
    # ------------------------------------------------------------------

    def add_attendance_record(
        self,
        employee_id: int,
        status: str,
        confidence: float,
        class_number: str = "",
    ) -> int:
        """Enregistre une présence.

        Args:
            employee_id: ID de l'employé.
            status: ``'IN_TIME'`` ou ``'LATE'``.
            confidence: Score de confiance de la reconnaissance (0.0–1.0).
            class_number: Numéro de classe associé au pointage.

        Returns:
            ID de l'enregistrement créé.
        """
        now = datetime.now()
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO attendance_records
               (employee_id, timestamp, date, status, confidence, class_number)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                employee_id,
                now.isoformat(),
                now.strftime("%Y-%m-%d"),
                status,
                confidence,
                class_number or "",
            ),
        )
        self._conn.commit()
        record_id = cursor.lastrowid
        logger.info(
            "Présence enregistrée : employee_id=%d, status=%s, confidence=%.2f.",
            employee_id, status, confidence,
        )
        return record_id

    def get_last_checkin(self, employee_name: str) -> Optional[datetime]:
        """Retourne l'heure du dernier pointage d'un employé.

        Args:
            employee_name: Nom de l'employé.

        Returns:
            ``datetime`` du dernier pointage ou ``None``.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """SELECT ar.timestamp
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               WHERE e.name = ?
               ORDER BY ar.timestamp DESC
               LIMIT 1""",
            (employee_name,),
        )
        row = cursor.fetchone()
        if row:
            return datetime.fromisoformat(row["timestamp"])
        return None

    def get_today_attendance(self) -> list[dict]:
        """Retourne toutes les présences du jour.

        Returns:
            Liste de dicts avec nom, heure, statut, confiance.
        """
        today = date.today().strftime("%Y-%m-%d")
        cursor = self._conn.cursor()
        cursor.execute(
            """SELECT e.name, ar.timestamp, ar.status, ar.confidence,
                      ar.class_number
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               WHERE ar.date = ?
               ORDER BY ar.timestamp ASC""",
            (today,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_stats_today(self) -> dict:
        """Retourne les statistiques de présence du jour.

        Returns:
            Dict ``{total: int, in_time: int, late: int}``.
        """
        today = date.today().strftime("%Y-%m-%d")
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as total FROM attendance_records WHERE date = ?",
            (today,),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM attendance_records WHERE date = ? AND status = 'IN_TIME'",
            (today,),
        )
        in_time = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM attendance_records WHERE date = ? AND status = 'LATE'",
            (today,),
        )
        late = cursor.fetchone()["cnt"]

        return {"total": total, "in_time": in_time, "late": late}

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def backup_database(self) -> str:
        """Crée une sauvegarde datée de la base de données.

        Returns:
            Chemin du fichier de sauvegarde.
        """
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"presence_backup_{timestamp}.db")
        shutil.copy2(self.db_path, backup_path)
        logger.info("Sauvegarde créée : %s", backup_path)
        return backup_path

    def verify_integrity(self) -> bool:
        """Vérifie l'intégrité de la base SQLite.

        Returns:
            ``True`` si la base est intègre, ``False`` sinon.
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            is_ok = result == "ok"
            if is_ok:
                logger.info("Intégrité de la base vérifiée : OK.")
            else:
                logger.error("Problème d'intégrité : %s", result)
            return is_ok
        except Exception as e:
            logger.error("Erreur lors de la vérification d'intégrité : %s", e)
            return False

    def close(self) -> None:
        """Ferme la connexion à la base de données."""
        if self._conn:
            self._conn.close()
            logger.info("Connexion à la base fermée.")

    def __del__(self) -> None:
        """Ferme la connexion lors de la destruction de l'objet."""
        try:
            self.close()
        except Exception:
            pass
