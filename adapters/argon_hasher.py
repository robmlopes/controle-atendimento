"""Argon2id password hashing."""

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class ArgonHasher:
    def __init__(self) -> None:
        self._argon = Argon2()

    def hash(self, password: str) -> str:
        return self._argon.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._argon.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            return False
