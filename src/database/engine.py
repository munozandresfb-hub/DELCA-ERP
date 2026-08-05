import logging
import logging.handlers
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

# ─── Logging Configuration ─────────────────────────────────────────────
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

_log_handler = logging.handlers.RotatingFileHandler(
    settings.LOG_DIR / "delca.log",
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8",
)
_log_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.WARNING)
_root_logger.addHandler(_log_handler)

# Silence overly verbose loggers
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

# ─── Database ──────────────────────────────────────────────────────────
DATABASE_URL = settings.DATABASE_URL
DB_PATH = settings.db_path

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    connect_args={"check_same_thread": False} if settings.is_sqlite else {},
)


def _migrate_sqlite_schema(cursor) -> None:
    """Apply missing columns to existing tables (idempotent)."""
    missing_columns: dict[str, list[tuple[str, str, str]]] = {
        "productos": [
            ("stock_minimo", "NUMERIC(12,2)", "0"),
        ],
        "movimientos_inventario": [
            ("documento_id", "INTEGER", "NULL"),
        ],
    }

    for table, columns in missing_columns.items():
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cursor.fetchall()}
            for col_name, col_type, col_default in columns:
                if col_name not in existing:
                    sql = (
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN {col_name} {col_type} DEFAULT {col_default}"
                    )
                    cursor.execute(sql)
        except Exception:
            pass  # Table may not exist yet on fresh DB


@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_connection, _connection_record) -> None:
    """Enable WAL mode and apply lightweight migrations."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")

    # ── Schema migrations (idempotent) ──────────────────────────
    if settings.is_sqlite:
        _migrate_sqlite_schema(cursor)

    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager for DB sessions. Closes session automatically."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()