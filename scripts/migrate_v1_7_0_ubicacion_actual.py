"""
Migration v1.7.0 — Add ubicacion_actual column to llantas table
and populate from existing UbicacionLlanta history.
"""

from sqlalchemy import text

from src.database.engine import get_session


def run_migration() -> None:
    with get_session() as session:
        # Add column (SQLite ignores IF NOT EXISTS for ALTER TABLE)
        try:
            session.execute(text(
                "ALTER TABLE llantas ADD COLUMN ubicacion_actual VARCHAR(50) DEFAULT 'RECEPCION'"
            ))
        except Exception:
            session.rollback()
            print("[migrate_v1.7.0] Columna ubicacion_actual ya existe, continuando…")
            return

        # Populate from latest UbicacionLlanta per tire
        session.execute(text("""
            UPDATE llantas
            SET ubicacion_actual = (
                SELECT ubicacion FROM ubicacion_llanta
                WHERE ubicacion_llanta.llanta_id = llantas.id
                ORDER BY ubicacion_llanta.fecha DESC
                LIMIT 1
            )
        """))

        session.commit()
        print("[migrate_v1.7.0] Columna ubicacion_actual agregada y poblada correctamente")
