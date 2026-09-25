"""
Backup & Recovery Service for DELCA ERP.

Provides automatic daily backups, manual backup/restore, CSV/Excel export,
integrity verification, and recovery management.
"""

import csv
import json
import msvcrt
import os
import shutil
import sqlite3
import time
from collections import defaultdict
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


def _acquire_backup_lock(timeout: float = 5.0) -> int | None:
    """Adquiere un lock exclusivo sobre backups/.backup.lock (Windows, msvcrt).

    Previene la race condition multi-instancia: 2-3 usuarios en red local
    disparan create_backup() al mismo tiempo (arranque +3s, timer 6h, vista
    Backup +5s) y generaban backups duplicados en el mismo segundo.

    Retorna el fd del lock si se obtuvo; None si otro proceso ya está
    haciendo backup (timeout agotado).
    """
    lock_path = BACKUP_DIR / ".backup.lock"
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            # msvcrt.locking requiere al menos 1 byte en el archivo
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
                os.fsync(fd)
            deadline = time.monotonic() + timeout
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    return fd
                except OSError:
                    if time.monotonic() >= deadline:
                        os.close(fd)
                        return None
                    time.sleep(0.2)
        except Exception:
            os.close(fd)
            return None
    except Exception:
        return None


def _release_backup_lock(fd: int) -> None:
    """Libera el lock de backup (LK_UNLCK + cierre del fd)."""
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except Exception:
        pass
    finally:
        try:
            os.close(fd)
        except Exception:
            pass


def _get_today_backup() -> Path | None:
    """Devuelve el backup automático de hoy si ya existe (dedupe por día)."""
    today = _today_key()
    for f in sorted(BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"), reverse=True):
        if today in f.stem and not f.stem.startswith(f"{BACKUP_PREFIX}pre_"):
            return f
    return None


def create_backup() -> tuple[bool, str]:
    """
    Create a timestamped backup of delca.db.

    Steps:
        1. Acquire exclusive lock (prevents multi-instance duplicates).
        2. Double-check: if today's backup already exists, skip.
        3. WAL checkpoint (TRUNCATE) to flush WAL into main DB.
        4. Copy delca.db → backups/delca_YYYYMMDD_HHMMSS.db.
        5. Prune backups older than MAX_BACKUPS days (1 per day).
        6. Record last backup timestamp.

    Returns:
        (True, backup_path) on success, (False, error_msg) on failure.
    """
    fd = _acquire_backup_lock()
    if fd is None:
        return False, "Backup en curso por otra instancia. Omitido."
    try:
        # Double-checked locking: otro proceso pudo crear el backup de hoy
        # mientras esperábamos el lock.
        existing = _get_today_backup()
        if existing:
            return True, f"Ya existe backup de hoy: {existing.name}"

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
    finally:
        _release_backup_lock(fd)


def _record_last_backup(timestamp: str) -> None:
    """Persist the last backup timestamp as JSON."""
    try:
        LAST_BACKUP_FILE.write_text(
            json.dumps({"last_backup": timestamp, "date": str(datetime.now())})
        )
    except Exception:
        pass  # non-critical


def _prune_old_backups() -> None:
    """Mantener 30 DÍAS de cobertura: 1 backup (el más reciente) por día.

    Antes se retenían MAX_BACKUPS=30 ARCHIVOS, pero con múltiples backups por
    día (race condition) la cobertura se reducía a ~5 días. Ahora se conserva
    el backup más reciente de cada día y se borran los días más antiguos.
    """
    by_day: dict[str, list[Path]] = defaultdict(list)
    for f in BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"):
        if f.stem.startswith(f"{BACKUP_PREFIX}pre_"):
            continue  # backups pre-migración se conservan aparte
        parts = f.stem.split("_")
        if len(parts) >= 2:
            by_day[parts[1]].append(f)

    # Conservar el más reciente de cada día
    keep: list[Path] = []
    for day, files in by_day.items():
        latest = max(files, key=lambda p: p.stat().st_mtime)
        keep.append(latest)
        for f in files:
            if f != latest:
                f.unlink(missing_ok=True)

    # Borrar los días más antiguos hasta dejar ≤ 30
    keep.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in keep[MAX_BACKUPS:]:
        old.unlink(missing_ok=True)


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
            # Headers vía PRAGMA MIENTRAS la conexión está viva (la tabla
            # puede estar vacía; antes se consultaba con la conexión cerrada
            # y lanzaba sqlite3.ProgrammingError). d[1] es el NOMBRE de la
            # columna (d[0] es el cid).
            headers = [d[1] for d in conn.execute(
                f"PRAGMA table_info([{table}])"
            ).fetchall()]
        finally:
            conn.close()

        if not rows:
            # Write headers-only CSV
            Path(output_path).write_text(
                ",".join(f'"{col}"' for col in headers) + "\n",
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
    # Formato sin guiones: coincide con el nombre del backup
    # (delca_YYYYMMDD_HHMMSS.db). Con guiones (YYYY-MM-DD) nunca
    # coincidiría con el nombre del archivo.
    return datetime.now().strftime("%Y%m%d")


def was_backup_done_today() -> bool:
    """Check if a daily backup has already been created today.

    Solo cuenta backups AUTOMÁTICOS (delca_YYYYMMDD_*.db), no los
    pre-migración (delca_pre_*_YYYYMMDD_*.db) que crean los scripts
    de migración como punto de restauración.
    """
    today = _today_key()
    for f in BACKUP_DIR.glob(f"{BACKUP_PREFIX}*.db"):
        if today in f.stem and not f.stem.startswith(f"{BACKUP_PREFIX}pre_"):
            return True
    return False
