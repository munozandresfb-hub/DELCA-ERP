"""BackupService unit tests — backup creation, restore, integrity check."""

import os
import sqlite3
import tempfile
from datetime import datetime
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
    def _setup(self, tmp_path, monkeypatch):
        """Aísla el módulo de backup en un directorio temporal (nunca toca producción)."""
        import src.core.services.backup_service as bs

        self.tmpdir = tmp_path
        backup_dir = tmp_path / "backups"
        monkeypatch.setattr(bs, "BACKUP_DIR", backup_dir)
        monkeypatch.setattr(bs, "LAST_BACKUP_FILE", backup_dir / ".last_backup.json")
        monkeypatch.setattr(bs, "DB_PATH", tmp_path / "delca.db")

        # Create a valid SQLite database for testing
        conn = sqlite3.connect(tmp_path / "delca.db")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

        yield

    def test_create_backup(self):
        success, path = create_backup()
        assert success
        backup_path = Path(path)
        assert backup_path.exists()
        assert backup_path.suffix == ".db"

    def test_create_backup_dedupe_same_day(self):
        """Dos create_backup el mismo día → 1 solo archivo (dedupe por día)."""
        success1, path1 = create_backup()
        assert success1
        success2, msg2 = create_backup()
        assert success2
        assert "Ya existe backup de hoy" in msg2
        backups = list_backups()
        assert len(backups) == 1

    def test_list_backups(self):
        """list_backups lista archivos de días distintos."""
        create_backup()
        # Simular un backup de un día anterior (archivo manual con nombre de ayer)
        yesterday = self.tmpdir / "backups" / "delca_20000101_000000_000000.db"
        yesterday.touch()
        backups = list_backups()
        assert len(backups) >= 2

    def test_backup_includes_date_in_name(self):
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
