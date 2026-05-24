"""Fernet symmetric encryption for settings at rest.

All secrets (API keys, tokens, credentials) are stored encrypted in the
`settings` table. The master key comes from the single required env var
DISPATCH_MASTER_KEY.
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)


def _derive_fernet_key(master_key: str) -> bytes:
    """Derive a URL-safe base64-encoded 32-byte Fernet key from the master key.

    Fernet requires a 32-byte base64-encoded key. We derive it deterministically
    from DISPATCH_MASTER_KEY so the same env var works across restarts.
    """
    raw = hashlib.sha256(master_key.encode()).digest()
    return base64.urlsafe_b64encode(raw)


class Crypto:
    """Encrypt/decrypt helper bound to a master key."""

    def __init__(self, master_key: str) -> None:
        self._fernet = Fernet(_derive_fernet_key(master_key))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext. Raises InvalidToken on bad key or tampering."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def rotate(self, old_crypto: "Crypto", ciphertext: str) -> str:
        """Re-encrypt ciphertext that was encrypted with *old_crypto*."""
        plaintext = old_crypto.decrypt(ciphertext)
        return self.encrypt(plaintext)
