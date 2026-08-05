"""
Migration script: v0.1.0 → v1.0.0 schema sync.

Adds missing columns to `usuarios` table:
  - password_changed_at       DATETIME
  - last_login                DATETIME
  - requires_password_change  BOOLEAN  (default 1 = True for existing)
  - failed_attempts           INTEGER  (default 0)
  - locked_until              DATETIME

Safe to re-run — uses IF NOT EXISTS style via try/except on each ALTER.
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.engine import SessionLocal, engine
from sqlalchemy import text, inspect

MIGRATIONS = [
    ("password_changed_at", "DATETIME", None),
    ("last_login", "DATETIME", None),
    ("requires_password_change", "BOOLEAN", "1"),   # force password change on existing users
    ("failed_attempts", "INTEGER", "0"),
    ("locked_until", "DATETIME", None),
]

def get_existing_columns():
    insp = inspect(engine)
    return {c["name"] for c in insp.get_columns("usuarios")}

def run_migration():
    existing = get_existing_columns()
    pending = [(name, typ, dflt) for name, typ, dflt in MIGRATIONS if name not in existing]

    if not pending:
        print("[OK] Migracion v1.0.0 ya aplicada — saltando.")
        return True

    print(f"[migracion] Columnas a agregar a usuarios: {[c[0] for c in pending]}")
    with SessionLocal() as session:
        for col_name, col_type, default in pending:
            sql = f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_type}"
            if default is not None:
                sql += f" DEFAULT {default}"
            print(f"  Ejecutando: {sql}")
            session.execute(text(sql))
        session.commit()

    # Verify
    after = get_existing_columns()
    for name, _, _ in pending:
        assert name in after, f"Column {name} was not created!"
    print("[OK] Migracion v1.0.0 aplicada correctamente.")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("DELCA ERP — Schema Migration v1.0.0")
    print("=" * 50)
    success = run_migration()
    sys.exit(0 if success else 1)
