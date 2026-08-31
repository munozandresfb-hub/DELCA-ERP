"""
Backup & Recovery Service for DELCA ERP.

Provides automatic daily backups, manual backup/restore, CSV/Excel export,
integrity verification, and recovery management.
"""

import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.database.engine import DB_PATH, get_session

BACKUP_DIR = settings.BACKUP_DIR
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LAST_BACKUP_FILE = BACKUP_DIR / ".last_backup.json"
MAX_BACKUPS = 30
BACKUP_PREFIX = "delca_"

# ─── Tables available for export ───────────────────────────────────────
ALL_TABLES = [
    "roles", "usuarios", "cliente", "llantas", "estados_llanta",
    "ubicaciones_llanta", "facturas", "pagos", "productos",
    "movimientos_inventario", "auditoria", "reglas_automatizacion", "alertas",
]


# ======================================================================
#  Backup
# ======================================================================

def _wal_checkpoint() -> None:
    """Run WAL checkpoint to flush WAL into main DB before backup."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def create_backup() -> tuple[bool, str]:
    """
    Create a timestamped backup of delca.db.

    Steps:
        1. WAL checkpoint (TRUNCATE) to flush WAL into main DB.
        2. Copy delca.db → backups/delca_YYYYMMDD_HHMMSS.db.
        3. Prune backups older than MAX_BACKUPS.
        4. Record last backup timestamp.

    Returns:
        (True, backup_path) on success, (False, error_msg) on failure.
    """
    try:
        _wal_checkpoint()

        if not DB_PATH.exists():
            return False, f"Database not found: {DB_PATH}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = BACKUP_DIR / f"{BACKUP_PREFIX}{timestamp}.db"

        shutil.copy2(str(DB_PATH), str(backup_path))

        _record_last_backup(timestamp)
        _prune_old_backups()

        return True, str(backup_path)
    except Exception as e:
        return False, f"Backup failed: {e}"


def _record_last_backup(timestamp: str) -> None:
    """Persist the last backup timestamp as JSON."""
    try:
        LAST_BACKUP_FILE.write_text(
            json.dumps({"last_backup": timestamp, "date": str(datetime.now())})
        )
    except Exception:
        pass  # non-critical


def _prune_old_backups() -> None:
    """Delete oldest backups beyond MAX_BACKUPS retention count."""
    backups = sorted(BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"))
    while len(backups) > MAX_BACKUPS:
        backups[0].unlink(missing_ok=True)
        backups.pop(0)


def get_last_backup_time() -> str | None:
    """Return the timestamp of the last backup, or None."""
    try:
        data = json.loads(LAST_BACKUP_FILE.read_text())
        return data.get("date")
    except Exception:
        # Fallback: scan directory
        backups = list(BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"))
        if backups:
            return datetime.fromtimestamp(
                max(b.stat().st_mtime for b in backups)
            ).strftime("%Y-%m-%d %H:%M:%S")
        return None


# ======================================================================
#  Restore
# ======================================================================

def _is_valid_sqlite(path: Path) -> bool:
    """Check if file starts with SQLite magic header."""
    try:
        header = path.read_bytes()[:16]
        return header == b"SQLite format 3\0"
    except Exception:
        return False


def list_backups() -> list[dict[str, Any]]:
    """List available backup files with metadata."""
    backups = []
    for f in sorted(BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"), reverse=True):
        backups.append({
            "name": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "size_display": _format_size(f.stat().st_size),
            "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        })
    return backups


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def restore_backup(backup_path: str) -> tuple[bool, str]:
    """
    Restore a backup file as the active database.

    Safety:
        1. Validate that backup is a valid SQLite file.
        2. Rename current delca.db → delca.db.bak (safety net).
        3. Copy backup to delca.db.
        4. Verify integrity of restored DB.

    CRITERION: Recovery in under 5 minutes.
    """
    backup = Path(backup_path)
    if not backup.exists():
        return False, f"Backup not found: {backup_path}"
    if not _is_valid_sqlite(backup):
        return False, f"Invalid backup file (not SQLite): {backup_path}"

    bak_path = None
    try:
        # Safety: rename current DB to .bak
        if DB_PATH.exists():
            bak_path = DB_PATH.with_suffix(".db.bak")
            bak_path.unlink(missing_ok=True)
            DB_PATH.rename(bak_path)

        # Copy backup as new live DB
        shutil.copy2(str(backup), str(DB_PATH))

        # Verify integrity
        conn = sqlite3.connect(str(DB_PATH))
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if row and row[0] != "ok":
                # Restore .bak
                if bak_path is not None and bak_path.exists():
                    DB_PATH.unlink(missing_ok=True)
                    bak_path.rename(DB_PATH)
                return False, f"Integrity check failed: {row[0]}"
        finally:
            conn.close()

        return True, f"Restored from {backup.name}"
    except Exception as e:
        return False, f"Restore failed: {e}"


# ======================================================================
#  Integrity
# ======================================================================

def verify_integrity() -> tuple[bool, str]:
    """Run PRAGMA integrity_check on the live database."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if row and row[0] == "ok":
                return True, "Integrity check passed"
            return False, f"Integrity issue: {row[0] if row else 'unknown'}"
        finally:
            conn.close()
    except Exception as e:
        return False, f"Could not verify integrity: {e}"


# ======================================================================
#  CSV Export
# ======================================================================

def export_to_csv(table: str, output_path: str) -> tuple[bool, str]:
    """Export a single table to CSV with headers."""
    if table not in ALL_TABLES:
        return False, f"Unknown table: {table}"

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(f"SELECT * FROM [{table}]").fetchall()
        finally:
            conn.close()

        if not rows:
            # Write headers-only CSV
            Path(output_path).write_text(
                ",".join(
                    f'"{col}"' for col in [d[0] for d in conn.execute(
                        f"PRAGMA table_info([{table}])"
                    ).fetchall()]
                )
                + "\n",
                encoding="utf-8-sig",
            )
            return True, f"Exported {table} (0 rows)"

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(row)

        return True, f"Exported {table} ({len(rows)} rows)"
    except Exception as e:
        return False, f"CSV export failed: {e}"


# ======================================================================
#  Excel Export
# ======================================================================

def export_to_excel(table: str, output_path: str) -> tuple[bool, str]:
    """Export a single table to XLSX using openpyxl."""
    if table not in ALL_TABLES:
        return False, f"Unknown table: {table}"

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return False, "openpyxl not installed. Run: pip install openpyxl"

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(f"SELECT * FROM [{table}]").fetchall()
        finally:
            conn.close()

        wb = Workbook()
        ws = wb.active
        ws.title = table[:31]  # Excel sheet name limit

        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append(list(row))
        else:
            ws.append(["No data"])

        # Auto-adjust column widths
        for i, col in enumerate(ws.columns, 1):
            max_length = 0
            for cell in col:
                try:
                    max_length = max(max_length, len(str(cell.value or "")))
                except Exception:
                    pass
            ws.column_dimensions[get_column_letter(i)].width = min(
                max_length + 2, 60
            )

        wb.save(output_path)
        return True, f"Exported {table} ({len(rows) if rows else 0} rows)"
    except Exception as e:
        return False, f"Excel export failed: {e}"


def export_all_tables(directory: str) -> dict[str, str]:
    """
    Export all 13 tables to individual CSV files in the given directory.

    Returns {table_name: file_path}.
    """
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}

    for table in ALL_TABLES:
        csv_path = str(out_dir / f"{table}.csv")
        ok, _ = export_to_csv(table, csv_path)
        if ok:
            results[table] = csv_path

    return results


# ======================================================================
#  Daily auto-backup scheduler helpers
# ======================================================================

def _today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def was_backup_done_today() -> bool:
    """Check if a daily backup has already been created today."""
    today = _today_key()
    for f in BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"):
        if today in f.stem:  # delca_20260624_*.db
            return True
    return False
