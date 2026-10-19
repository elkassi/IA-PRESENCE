"""
Embedding Cipher — Chiffrement AES-256 des embeddings biométriques.

Conformité RGPD : les données biométriques (embeddings faciaux) sont
stockées localement et chiffrées avec AES-256-CBC via la bibliothèque
``cryptography`` (Fernet).

Usage::

    cipher = EmbeddingCipher()
    encrypted = cipher.encrypt(embedding_array)
    decrypted = cipher.decrypt(encrypted)
"""

import hashlib
import base64
import logging
from typing import Optional

import numpy as np
from cryptography.fernet import Fernet

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)


class EmbeddingCipher:
    """Chiffre et déchiffre les embeddings faciaux avec AES-256 (Fernet).

    Attributes:
        _fernet: Instance Fernet initialisée avec la clé dérivée.
    """

    def __init__(self, key: Optional[str] = None) -> None:
        """Initialise le cipher avec une clé de chiffrement.

        Args:
            key: Clé en clair. Si ``None``, utilise ``ENCRYPTION_KEY``
                 depuis ``config.py``.
        """
        raw_key = key or ENCRYPTION_KEY
        # Dériver une clé Fernet valide (32 bytes base64) à partir de la clé brute
        derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        self._fernet = Fernet(fernet_key)
        logger.info("EmbeddingCipher initialisé.")

    def encrypt(self, embedding: np.ndarray) -> bytes:
        """Chiffre un embedding numpy en bytes.

        Args:
            embedding: Vecteur numpy (ex: 512-dim FaceNet512).

        Returns:
            Données chiffrées (bytes).

        Raises:
            ValueError: Si l'embedding est vide ou invalide.
        """
        if embedding is None or embedding.size == 0:
            raise ValueError("L'embedding ne peut pas être vide.")

        try:
            raw_bytes = embedding.tobytes()
            # Stocker aussi le dtype et le shape pour la reconstruction
            metadata = f"{embedding.dtype}|{','.join(map(str, embedding.shape))}".encode("utf-8")
            payload = metadata + b"|||" + raw_bytes
            encrypted = self._fernet.encrypt(payload)
            logger.info("Embedding chiffré avec succès (%d bytes).", len(encrypted))
            return encrypted
        except Exception as e:
            logger.error("Erreur lors du chiffrement : %s", e)
            raise

    def decrypt(self, encrypted_data: bytes) -> np.ndarray:
        """Déchiffre des bytes en embedding numpy.

        Args:
            encrypted_data: Données chiffrées par ``encrypt()``.

        Returns:
            Vecteur numpy reconstruit.

        Raises:
            ValueError: Si les données sont corrompues ou invalides.
        """
        if not encrypted_data:
            raise ValueError("Les données chiffrées ne peuvent pas être vides.")

        try:
            payload = self._fernet.decrypt(encrypted_data)
            metadata_bytes, raw_bytes = payload.split(b"|||", 1)
            metadata = metadata_bytes.decode("utf-8")
            dtype_str, shape_str = metadata.split("|")
            shape = tuple(int(s) for s in shape_str.split(","))
            embedding = np.frombuffer(raw_bytes, dtype=np.dtype(dtype_str)).reshape(shape)
            logger.info("Embedding déchiffré avec succès (shape=%s).", shape)
            return embedding
        except Exception as e:
            logger.error("Erreur lors du déchiffrement : %s", e)
            raise ValueError(f"Impossible de déchiffrer l'embedding : {e}") from e
