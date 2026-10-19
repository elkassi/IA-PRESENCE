"""
Configuration globale — IA-PRESENCE.

Centralise tous les paramètres de l'application :
horaires, seuils IA, chemins fichiers, sécurité.
"""

import os
import platform
import logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s"

# ---------------------------------------------------------------------------
# Horaires & règles métier
# ---------------------------------------------------------------------------

# Heure limite (HH:MM) pour statut IN TIME / LATE
HEURE_LIMITE = "08:30"

# Cooldown anti-doublons (en minutes)
COOLDOWN_MINUTES = 30

# Numéro de classe par défaut pour les pointages
DEFAULT_CLASS_NUMBER = "1"

# ---------------------------------------------------------------------------
# Enrôlement
# ---------------------------------------------------------------------------

# Nombre de photos minimum pour l'enrôlement
PHOTOS_MIN_ENROLLMENT = 50

# ---------------------------------------------------------------------------
# Reconnaissance faciale (DeepFace / FaceNet512)
# ---------------------------------------------------------------------------

# Seuil de distance DeepFace (plus bas = plus strict)
DISTANCE_THRESHOLD = 0.40

# Traiter 1 frame sur N pour les performances
FRAME_SKIP = 3

# Modèle de reconnaissance
FACE_MODEL = "Facenet512"

# Détecteur de visages
FACE_DETECTOR = "opencv"

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

# Répertoire racine du projet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chemin base de données
DB_PATH = os.path.join(BASE_DIR, "database", "presence.db")

# Dossier données employés
EMPLOYEES_DIR = os.path.join(BASE_DIR, "data", "employees")

# Dossier exports Excel
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

# ---------------------------------------------------------------------------
# Sécurité / Chiffrement
# ---------------------------------------------------------------------------

# Clé de chiffrement AES-256 (générer une vraie clé en prod)
ENCRYPTION_KEY = os.environ.get("IA_PRESENCE_ENCRYPTION_KEY", "CHANGE_ME_IN_PRODUCTION")

# ---------------------------------------------------------------------------
# Détection plateforme (macOS Apple Silicon vs autre)
# ---------------------------------------------------------------------------


def detect_backend() -> str:
    """Détecte automatiquement le backend TensorFlow optimal.

    Returns:
        'apple_silicon' si macOS ARM64, sinon 'cpu'.
    """
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin" and machine == "arm64":
        return "apple_silicon"
    return "cpu"


BACKEND = detect_backend()

# ---------------------------------------------------------------------------
# Interface graphique
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
APP_TITLE = "IA-PRESENCE — Gestion de Présence par Reconnaissance Faciale"

COLORS = {
    "bg_primary":   "#1a1a2e",   # Fond principal (dark navy)
    "bg_secondary": "#16213e",   # Fond cartes
    "bg_tertiary":  "#0f3460",   # Fond éléments secondaires
    "accent":       "#7c3aed",   # Violet principal
    "accent_hover": "#6d28d9",   # Violet hover
    "success":      "#10b981",   # Vert IN TIME
    "warning":      "#f59e0b",   # Orange LATE
    "text_primary": "#f1f5f9",   # Texte principal
    "text_muted":   "#94a3b8",   # Texte secondaire
    "border":       "#334155",   # Bordures
}
