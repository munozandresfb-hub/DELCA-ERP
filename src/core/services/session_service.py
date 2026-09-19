"""
Session management service for DELCA ERP.

Tracks user session, inactivity timeout, and provides session locking.
"""

import time
from datetime import datetime, timedelta
from typing import Any

from src.core.services.audit_service import registrar_logout


class SessionManager:
    """
    Singleton session manager.

    Tracks the current user, last activity time, and provides
    inactivity-based auto-lock.
    """

    _instance: "SessionManager | None" = None

    INACTIVITY_TIMEOUT_SECONDS = 1800  # 30 minutes (fallback)

    # Timeout por rol (segundos). None = nunca expira.
    ROLE_TIMEOUTS = {
        "ADMIN": 1800,           # 30 min
        "Gerencia": 10800,       # 3 horas
        "Operador": None,        # sin cierre
    }

    def __new__(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._user = None
            cls._instance._last_activity = time.time()
            cls._instance._locked = False
            cls._instance._login_time = None
        return cls._instance

    # ── User management ────────────────────────────────────────────

    def set_user(self, user: Any) -> None:
        """Set the active user and record login time."""
        self._user = user
        self._login_time = datetime.now()
        self._locked = False
        self.update_activity()

    def get_user(self) -> Any:
        """Return the current user object."""
        return self._user

    def get_user_id(self) -> int | None:
        """Return the current user's ID."""
        if self._user and hasattr(self._user, "id"):
            return self._user.id
        return None

    def get_username(self) -> str:
        """Return the current user's username."""
        if self._user and hasattr(self._user, "username"):
            return self._user.username
        return ""

    def get_timeout_seconds(self) -> int | None:
        """Return timeout for the current user's role, or None if no timeout."""
        if not self._user:
            return self.INACTIVITY_TIMEOUT_SECONDS
        try:
            rol_name = self._user.rol.nombre
            return self.ROLE_TIMEOUTS.get(rol_name, self.INACTIVITY_TIMEOUT_SECONDS)
        except Exception:
            return self.INACTIVITY_TIMEOUT_SECONDS

    def clear_session(self, session: Any | None = None) -> None:
        """Clear the session (logout). Records audit if user was set."""
        user_id = self.get_user_id()
        if user_id is not None:
            registrar_logout(user_id, session=session)
        self._user = None
        self._last_activity = time.time()
        self._locked = False
        self._login_time = None

    # ── Activity tracking ──────────────────────────────────────────

    # Mínimo intervalo (s) entre actualizaciones para no saturar con MouseMove.
    MIN_ACTIVITY_INTERVAL_SECONDS = 2.0

    def update_activity(self) -> None:
        """Reset the inactivity timer (throttled)."""
        now = time.time()
        if now - self._last_activity < self.MIN_ACTIVITY_INTERVAL_SECONDS:
            return
        self._last_activity = now

    def get_last_activity(self) -> float:
        """Return timestamp of last activity."""
        return self._last_activity

    def get_remaining_seconds(self) -> int:
        """Return seconds remaining before auto-lock."""
        if self._user is None:
            return 0
        timeout = self.get_timeout_seconds()
        if timeout is None:  # sin cierre para este rol
            return 999999
        elapsed = time.time() - self._last_activity
        remaining = timeout - elapsed
        return max(0, int(remaining))

    def is_session_expired(self) -> bool:
        """Check if the inactivity timeout has elapsed."""
        if self._user is None:
            return True
        timeout = self.get_timeout_seconds()
        if timeout is None:  # sin cierre para este rol
            return False
        elapsed = time.time() - self._last_activity
        return elapsed > timeout

    # ── Locking ────────────────────────────────────────────────────

    def lock(self) -> None:
        """Lock the session (triggers re-login)."""
        self._locked = True

    def unlock(self) -> None:
        """Unlock the session."""
        self._locked = False
        self.update_activity()

    def is_locked(self) -> bool:
        """Check if the session is currently locked."""
        return self._locked

    # ── Login info ─────────────────────────────────────────────────

    def get_login_time(self) -> datetime | None:
        """Return when the user logged in."""
        return self._login_time

    def get_session_duration(self) -> timedelta:
        """Return how long the user has been logged in."""
        if self._login_time is None:
            return timedelta()
        return datetime.now() - self._login_time


# Module-level convenience
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Return the singleton SessionManager instance."""
    return _session_manager
