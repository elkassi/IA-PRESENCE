"""
Tests — EmbeddingCipher.

Teste le chiffrement et déchiffrement AES-256 des embeddings.
"""

import os
import sys

import numpy as np
import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)

from security.embedding_cipher import EmbeddingCipher


class TestEmbeddingCipher:
    """Tests pour EmbeddingCipher."""

    @pytest.fixture
    def cipher(self):
        """Fournit une instance EmbeddingCipher."""
        return EmbeddingCipher(key="test_key_for_testing")

    def test_encrypt_returns_bytes(self, cipher, sample_embedding):
        """Le chiffrement retourne des bytes."""
        encrypted = cipher.encrypt(sample_embedding)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_decrypt_returns_ndarray(self, cipher, sample_embedding):
        """Le déchiffrement retourne un numpy array."""
        encrypted = cipher.encrypt(sample_embedding)
        decrypted = cipher.decrypt(encrypted)
        assert isinstance(decrypted, np.ndarray)

    def test_encrypt_decrypt_roundtrip(self, cipher, sample_embedding):
        """Chiffrement puis déchiffrement restaure l'original."""
        encrypted = cipher.encrypt(sample_embedding)
        decrypted = cipher.decrypt(encrypted)
        np.testing.assert_array_almost_equal(decrypted, sample_embedding)

    def test_encrypt_decrypt_shape_preserved(self, cipher):
        """La forme du tableau est préservée."""
        original = np.random.rand(512).astype(np.float64)
        encrypted = cipher.encrypt(original)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted.shape == original.shape

    def test_encrypt_decrypt_dtype_preserved(self, cipher):
        """Le dtype est préservé."""
        original = np.random.rand(512).astype(np.float32)
        encrypted = cipher.encrypt(original)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted.dtype == original.dtype

    def test_encrypted_data_different_from_original(self, cipher, sample_embedding):
        """Les données chiffrées sont différentes de l'original."""
        encrypted = cipher.encrypt(sample_embedding)
        original_bytes = sample_embedding.tobytes()
        assert encrypted != original_bytes

    def test_different_keys_produce_different_output(self, sample_embedding):
        """Deux clés différentes produisent des chiffrements différents."""
        cipher1 = EmbeddingCipher(key="key_one")
        cipher2 = EmbeddingCipher(key="key_two")
        enc1 = cipher1.encrypt(sample_embedding)
        enc2 = cipher2.encrypt(sample_embedding)
        assert enc1 != enc2

    def test_wrong_key_fails_decryption(self, sample_embedding):
        """Déchiffrement avec mauvaise clé lève une erreur."""
        cipher1 = EmbeddingCipher(key="correct_key")
        cipher2 = EmbeddingCipher(key="wrong_key")
        encrypted = cipher1.encrypt(sample_embedding)
        with pytest.raises(ValueError):
            cipher2.decrypt(encrypted)

    def test_encrypt_empty_embedding_raises(self, cipher):
        """Chiffrement d'un embedding vide lève une erreur."""
        empty = np.array([])
        with pytest.raises(ValueError):
            cipher.encrypt(empty)

    def test_decrypt_empty_data_raises(self, cipher):
        """Déchiffrement de données vides lève une erreur."""
        with pytest.raises(ValueError):
            cipher.decrypt(b"")

    def test_decrypt_corrupt_data_raises(self, cipher):
        """Déchiffrement de données corrompues lève une erreur."""
        with pytest.raises(ValueError):
            cipher.decrypt(b"corrupted_data_not_valid")

    def test_multiple_embeddings(self, cipher):
        """Plusieurs embeddings peuvent être chiffrés/déchiffrés."""
        embeddings = [np.random.rand(512) for _ in range(5)]
        for emb in embeddings:
            encrypted = cipher.encrypt(emb)
            decrypted = cipher.decrypt(encrypted)
            np.testing.assert_array_almost_equal(decrypted, emb)
