"""
Models — Schéma des tables SQLite pour IA-PRESENCE.

Tables :
    - ``employees``          : informations des employés enrôlés.
    - ``attendance_records`` : enregistrements de présence horodatés.
"""

# SQL de création des tables
CREATE_EMPLOYEES_TABLE = """
CREATE TABLE IF NOT EXISTS employees (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    department   TEXT    DEFAULT '',
    enrolled_at  TEXT    NOT NULL,
    active       INTEGER DEFAULT 1
);
"""

CREATE_ATTENDANCE_TABLE = """
CREATE TABLE IF NOT EXISTS attendance_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL,
    timestamp     TEXT    NOT NULL,
    date          TEXT    NOT NULL,
    status        TEXT    NOT NULL CHECK(status IN ('IN_TIME', 'LATE')),
    confidence    REAL    NOT NULL,
    class_number  TEXT    DEFAULT '',
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON attendance_records(date);
CREATE INDEX IF NOT EXISTS idx_attendance_employee
    ON attendance_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_employees_name
    ON employees(name);
"""
