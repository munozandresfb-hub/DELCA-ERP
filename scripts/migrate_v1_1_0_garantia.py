"""Migration v1.1.0: Add 'GARANTIA' to Factura estado constraint.

SQLite does not support ALTER TABLE for CHECK constraints,
so we recreate the table with the updated constraint.

Uses raw sqlite3 to avoid SQLAlchemy autobegin conflicts.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")


def run_migration() -> bool:
    """Add GARANTIA to the facturas estado check constraint.

    Returns True on success, False on failure.
    """
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        # 1. Create new table with updated constraint
        conn.execute("""
            CREATE TABLE facturas_v2 (
                id INTEGER NOT NULL,
                cliente_id INTEGER NOT NULL,
                numero VARCHAR(50) NOT NULL,
                fecha_emision DATETIME,
                total NUMERIC(12, 2) DEFAULT 0,
                saldo NUMERIC(12, 2) DEFAULT 0,
                estado VARCHAR(20) DEFAULT 'PENDIENTE',
                observaciones TEXT,
                created_at DATETIME,
                PRIMARY KEY (id),
                CHECK (estado IN ('PENDIENTE','PARCIAL','PAGADA','ANULADA','VENCIDA','GARANTIA')),
                FOREIGN KEY (cliente_id) REFERENCES cliente (id) ON DELETE RESTRICT
            );
        """)

        # 2. Copy data
        conn.execute("""
            INSERT INTO facturas_v2
            SELECT id, cliente_id, numero, fecha_emision, total, saldo,
                   estado, observaciones, created_at
            FROM facturas;
        """)

        # 3. Drop old table
        conn.execute("DROP TABLE facturas;")

        # 4. Rename new table
        conn.execute("ALTER TABLE facturas_v2 RENAME TO facturas;")

        # 5. Recreate indexes
        conn.execute("CREATE INDEX ix_facturas_cliente_id ON facturas (cliente_id);")
        conn.execute("CREATE INDEX ix_facturas_estado ON facturas (estado);")

        conn.commit()
        print("[OK] Migracion v1.1.0: constraint GARANTIA actualizado.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.1.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
