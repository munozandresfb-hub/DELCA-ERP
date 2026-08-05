"""BackupService unit tests — backup creation, restore, integrity check."""

import os
import tempfile
from pathlib import Path

import pytest

from src.core.services.backup_service import (
    create_backup,
    list_backups,
    verify_integrity,
)


class TestBackupService:
    """Backup and restore logic using a temporary directory."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        """Create a temp dir for each test, change to it, and set a fake DB."""
        self.tmpdir = tmp_path
        self.orig_cwd = Path.cwd()
        os.chdir(self.tmpdir)

        # Create a valid SQLite database for testing
        import sqlite3
        conn = sqlite3.connect("delca.db")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

        yield

        os.chdir(self.orig_cwd)

    def test_create_backup(self):
        success, path = create_backup()
        assert success
        backup_path = Path(path)
        assert backup_path.exists()
        assert backup_path.suffix == ".db"

    def test_list_backups(self):
        create_backup()
        create_backup()
        backups = list_backups()
        assert len(backups) >= 2

    def test_backup_includes_date_in_name(self):
        from datetime import datetime
        success, path = create_backup()
        assert success
        name = Path(path).stem
        today = datetime.now().strftime("%Y%m%d")
        assert today in name

    def test_integrity_check(self):
        """Verify integrity check passes on a good backup."""
        create_backup()
        ok, msg = verify_integrity()
        assert ok

    def test_list_backups_metadata(self):
        """list_backups should return dicts with size/date fields."""
        create_backup()
        backups = list_backups()
        entry = backups[0]
        assert "name" in entry or "nombre" in entry
        assert "size" in entry or "tamano" in entry
        assert "size_display" in entry
