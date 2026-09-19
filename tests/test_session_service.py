"""SessionManager unit tests — singleton, user tracking, inactivity."""

from src.core.services.session_service import SessionManager


class TestSessionManager:
    """SessionManager singleton and activity tracking."""

    def test_singleton(self):
        s1 = SessionManager()
        s2 = SessionManager()
        assert s1 is s2

    def test_initial_state(self):
        sm = SessionManager()
        assert sm.get_user() is None
        assert sm.get_user_id() is None
        assert sm.is_locked() is False

    def test_set_user(self):
        sm = SessionManager()
        mock_user = type("User", (), {"id": 1, "username": "test"})()
        sm.set_user(mock_user)
        assert sm.get_user() is mock_user
        assert sm.get_user_id() == 1
        assert sm.get_username() == "test"

    def test_clear_session(self, db_session):
        sm = SessionManager()
        mock_user = type("User", (), {"id": 1, "username": "test"})()
        sm.set_user(mock_user)
        sm.clear_session(session=db_session)
        assert sm.get_user() is None
        assert sm.get_username() == ""

    def test_activity_update(self, monkeypatch):
        sm = SessionManager()
        mock_user = type("User", (), {"id": 1, "username": "test"})()
        sm.set_user(mock_user)

        # Reloj controlado para evitar flakiness por resolución del sistema:
        # update_activity() tiene un throttle de 2s (MIN_ACTIVITY_INTERVAL_SECONDS),
        # así que un sleep real nunca garantiza que el timestamp cambie.
        fake_clock = {"now": 1000.0}
        monkeypatch.setattr(
            "src.core.services.session_service.time.time",
            lambda: fake_clock["now"],
        )
        sm.clear_session()  # resetea _last_activity al reloj fake (1000.0)
        sm.set_user(mock_user)

        before = sm.get_last_activity()
        fake_clock["now"] += 5.0  # supera el throttle de 2s
        sm.update_activity()
        after = sm.get_last_activity()

        assert before == 1000.0
        assert after == 1005.0
        assert after > before

    def test_not_expired_after_activity(self):
        sm = SessionManager()
        mock_user = type("User", (), {"id": 1, "username": "test"})()
        sm.set_user(mock_user)
        sm.update_activity()
        assert not sm.is_session_expired()

    def test_remaining_seconds_no_user(self, db_session):
        sm = SessionManager()
        sm.clear_session(session=db_session)  # ensure clean state for singleton
        assert sm.get_remaining_seconds() == 0

    def test_lock_unlock(self):
        sm = SessionManager()
        sm.lock()
        assert sm.is_locked()
        sm.unlock()
        assert not sm.is_locked()

    def test_login_time(self):
        sm = SessionManager()
        mock_user = type("User", (), {"id": 1, "username": "test"})()
        sm.set_user(mock_user)
        assert sm.get_login_time() is not None
        assert sm.get_session_duration().total_seconds() >= 0
