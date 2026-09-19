import re
from datetime import datetime, timedelta

import bcrypt

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64  # bcrypt solo usa los primeros 72 bytes
PASSWORD_EXPIRY_DAYS = 90
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    """Authentication and password management service."""

    # ── Password Hashing ───────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            raise ValueError("La contraseña supera el límite de 72 bytes")
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its bcrypt hash.

        Robust: un hash corrupto/vacío no rompe el login (devuelve False).
        """
        try:
            password_bytes = password.encode("utf-8")
            if len(password_bytes) > 72:
                return False
            return bcrypt.checkpw(
                password_bytes,
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    # ── Password Policy ────────────────────────────────────────────────

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password meets minimum strength requirements.

        Returns:
            (True, "") if valid, (False, error_message) if not.
        """
        if not password or len(password) < PASSWORD_MIN_LENGTH:
            return (
                False,
                f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres",
            )
        if len(password) > PASSWORD_MAX_LENGTH:
            return (
                False,
                f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres",
            )
        if not re.search(r"[A-Z]", password):
            return False, "La contraseña debe contener al menos una mayúscula"
        if not re.search(r"[a-z]", password):
            return False, "La contraseña debe contener al menos una minúscula"
        if not re.search(r"[0-9]", password):
            return False, "La contraseña debe contener al menos un número"
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
            return False, "La contraseña debe contener al menos un carácter especial"
        return True, ""

    @staticmethod
    def is_password_expired(usuario) -> bool:
        """Check if the user's password has expired (90 days)."""
        if usuario.password_changed_at is None:
            return True
        expiry = usuario.password_changed_at + timedelta(
            days=PASSWORD_EXPIRY_DAYS
        )
        return datetime.now() > expiry

    @staticmethod
    def change_password(
        usuario, new_password: str, session=None,
    ) -> tuple[bool, str]:
        """Change user's password with validation.

        Args:
            usuario: Usuario ORM object
            new_password: New password in plain text
            session: Optional DB session (if None, doesn't flush)

        Returns:
            (True, "") on success, (False, error) on failure.
        """
        valid, msg = AuthService.validate_password_strength(new_password)
        if not valid:
            return False, msg

        usuario.password_hash = AuthService.hash_password(new_password)
        usuario.password_changed_at = datetime.now()
        usuario.requires_password_change = False
        if session:
            session.flush()
        return True, ""

    # ── Account Lockout ────────────────────────────────────────────────

    @staticmethod
    def is_account_locked(usuario) -> bool:
        """Check if the account is temporarily locked."""
        if usuario.locked_until is None:
            return False
        if datetime.now() > usuario.locked_until:
            usuario.locked_until = None
            usuario.failed_attempts = 0
            return False
        return True

    @staticmethod
    def record_failed_attempt(usuario, session=None) -> bool:
        """Record a failed login attempt. Returns True if account now locked."""
        usuario.failed_attempts = (usuario.failed_attempts or 0) + 1
        if usuario.failed_attempts >= MAX_FAILED_ATTEMPTS:
            usuario.locked_until = datetime.now() + timedelta(
                minutes=LOCKOUT_MINUTES
            )
            if session:
                session.flush()
            return True  # locked
        if session:
            session.flush()
        return False  # not locked yet
