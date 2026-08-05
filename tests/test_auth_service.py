"""AuthService unit tests — password hashing, validation, lockout, expiry."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.modules.usuarios.services.auth_service import (
    AuthService,
    PASSWORD_MIN_LENGTH,
    MAX_FAILED_ATTEMPTS,
)
from src.modules.usuarios.models.usuario_model import Usuario


class TestPasswordStrength:
    """Password policy validation."""

    def test_min_length_fails(self):
        valid, msg = AuthService.validate_password_strength("Ab1!")
        assert not valid
        assert "8 caracteres" in msg

    def test_no_uppercase_fails(self):
        valid, msg = AuthService.validate_password_strength("abcdef1!@")
        assert not valid
        assert "mayúscula" in msg

    def test_no_lowercase_fails(self):
        valid, msg = AuthService.validate_password_strength("ABCDEF1!@")
        assert not valid
        assert "minúscula" in msg

    def test_no_digit_fails(self):
        valid, msg = AuthService.validate_password_strength("Abcdefgh!@")
        assert not valid
        assert "número" in msg

    def test_no_special_fails(self):
        valid, msg = AuthService.validate_password_strength("Abcdefgh1")
        assert not valid
        assert "especial" in msg

    def test_valid_password(self):
        valid, msg = AuthService.validate_password_strength("Str0ng!Pass")
        assert valid
        assert msg == ""

    def test_empty_password(self):
        valid, msg = AuthService.validate_password_strength("")
        assert not valid


class TestPasswordHashing:
    """Bcrypt hash/verify."""

    def test_hash_and_verify(self):
        pw = "Str0ng!Pass"
        hashed = AuthService.hash_password(pw)
        assert hashed != pw
        assert AuthService.verify_password(pw, hashed)

    def test_wrong_password_fails(self):
        hashed = AuthService.hash_password("Str0ng!Pass")
        assert not AuthService.verify_password("WrongPass1!", hashed)

    def test_different_hashes_per_call(self):
        pw = "Str0ng!Pass"
        h1 = AuthService.hash_password(pw)
        h2 = AuthService.hash_password(pw)
        assert h1 != h2  # bcrypt salts


class TestPasswordExpiry:
    """Password expiration logic."""

    def test_expired_when_none(self):
        user = Usuario(password_changed_at=None)
        assert AuthService.is_password_expired(user)

    def test_not_expired_within_90(self):
        user = Usuario(password_changed_at=datetime.now())
        assert not AuthService.is_password_expired(user)

    def test_expired_after_91_days(self):
        past = datetime.now() - timedelta(days=91)
        user = Usuario(password_changed_at=past)
        assert AuthService.is_password_expired(user)


class TestChangePassword:
    """Password change with validation."""

    def test_change_valid_password(self, db_session: Session, test_user: Usuario):
        ok, msg = AuthService.change_password(test_user, "NewStr0ng!", db_session)
        assert ok
        assert msg == ""
        assert AuthService.verify_password("NewStr0ng!", test_user.password_hash)
        assert test_user.requires_password_change is False
        assert test_user.password_changed_at is not None

    def test_change_weak_password_fails(self, db_session: Session, test_user: Usuario):
        ok, msg = AuthService.change_password(test_user, "weak", db_session)
        assert not ok
        assert msg


class TestAccountLockout:
    """Failed attempt tracking and lockout."""

    def test_failed_attempt_accumulates(self, db_session: Session, test_user: Usuario):
        AuthService.record_failed_attempt(test_user, db_session)
        assert test_user.failed_attempts == 1

    def test_lockout_after_max_attempts(self, db_session: Session, test_user: Usuario):
        locked = False
        for i in range(MAX_FAILED_ATTEMPTS):
            locked = AuthService.record_failed_attempt(test_user, db_session)
        assert locked
        assert test_user.locked_until is not None

    def test_is_account_locked(self, db_session: Session, locked_user: Usuario):
        assert AuthService.is_account_locked(locked_user)

    def test_not_locked(self, db_session: Session, test_user: Usuario):
        assert not AuthService.is_account_locked(test_user)
