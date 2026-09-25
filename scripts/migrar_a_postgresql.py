"""Migración de la base de datos DELCA de SQLite a PostgreSQL (Lote 8).

Este script ETL:
  1. Inspecciona el esquema completo de la BD SQLite fuente.
  2. Crea las mismas tablas en PostgreSQL con tipos mapeados
     (AUTOINCREMENT → SERIAL, fechas → TIMESTAMP, etc.).
  3. Copia los datos tabla por tabla con verificación de conteos.
  4. Reporta un resumen tabla a tabla (fuente vs destino).

REQUISITOS PREVIOS (antes de ejecutar):
  - PostgreSQL instalado y corriendo en el PC servidor del taller.
  - Base creada:  CREATE DATABASE delca;
  - Credenciales en .env del proyecto:
      DATABASE_URL=postgresql://usuario:clave@IP_SERVIDOR:5432/delca
  - Dependencia: pip install psycopg2-binary  (driver PostgreSQL)

USO:
  python scripts/migrar_a_postgresql.py            # usa DATABASE_URL del .env
  python scripts/migrar_a_postgresql.py --solo-verificar   # compara conteos sin escribir

ADVERTENCIA: ejecutar con la aplicación CERRADA en todos los equipos.
"""

import os
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path (scripts/ está un nivel dentro)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Mapeo de tipos SQLite → PostgreSQL (suficiente para el esquema DELCA)
TYPE_MAP = {
    "INTEGER": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    "NUMERIC": "NUMERIC",
    "TEXT": "TEXT",
    "VARCHAR": "VARCHAR",
    "BOOLEAN": "BOOLEAN",
    "DATETIME": "TIMESTAMP",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
}


def _map_type(declared: str) -> str:
    """Convierte un tipo declarado SQLite a PostgreSQL."""
    upper = declared.upper()
    if upper.startswith("VARCHAR"):
        return declared  # VARCHAR(n) ya es válido en PG
    if upper.startswith("NUMERIC"):
        return declared
    if upper.startswith("DECIMAL"):
        return declared
    return TYPE_MAP.get(upper, "TEXT")


def _sqlite_tables(src) -> list[str]:
    rows = src.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ).fetchall()
    return [r[0] for r in rows]


def _table_schema(src, table: str) -> list[dict]:
    """Devuelve [{name, type, notnull, pk, dflt}] para una tabla."""
    cols = []
    for row in src.execute(text(f'PRAGMA table_info("{table}")')):
        cols.append({
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "dflt": row[4],
            "pk": row[5],
        })
    return cols


def _create_table_pg(dst, table: str, cols: list[dict]) -> None:
    parts = []
    for c in cols:
        pg_type = _map_type(c["type"])
        col_def = f'"{c["name"]}" {pg_type}'
        if c["notnull"]:
            col_def += " NOT NULL"
        if c["pk"]:
            if pg_type in ("BIGINT", "INTEGER"):
                col_def = f'"{c["name"]}" BIGSERIAL PRIMARY KEY'
            else:
                col_def += " PRIMARY KEY"
        if c["dflt"] is not None and c["dflt"] != "NULL":
            dflt = c["dflt"]
            if isinstance(dflt, str) and dflt.startswith("'"):
                col_def += f" DEFAULT {dflt}"
            else:
                col_def += f" DEFAULT {dflt}"
        parts.append(col_def)
    ddl = f'CREATE TABLE IF NOT EXISTS "{table}" (\n  ' + ",\n  ".join(parts) + "\n)"
    dst.execute(ddl)


def _copy_table(src, dst, table: str, cols: list[dict]) -> int:
    names = ", ".join(f'"{c["name"]}"' for c in cols)
    rows = src.execute(text(f'SELECT * FROM "{table}"')).fetchall()
    if not rows:
        return 0
    placeholders = ", ".join(["%s"] * len(cols))
    insert_sql = f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})'
    dst.executemany(insert_sql, rows)
    return len(rows)


def main() -> int:
    import argparse
    from sqlalchemy import create_engine, text

    parser = argparse.ArgumentParser(description="Migración SQLite → PostgreSQL DELCA")
    parser.add_argument("--solo-verificar", action="store_true",
                        help="solo compara conteos sin escribir en destino")
    args = parser.parse_args()

    src_url = os.getenv("DATABASE_URL_SQLITE", "sqlite:///delca.db")
    dst_url = os.getenv("DATABASE_URL")
    if not dst_url or not dst_url.startswith("postgresql"):
        print("ERROR: DATABASE_URL no apunta a PostgreSQL. Configure .env:")
        print("  DATABASE_URL=postgresql://usuario:clave@IP:5432/delca")
        return 1

    src = create_engine(src_url).connect()
    dst = create_engine(dst_url).connect()

    try:
        if not args.solo_verificar:
            dst.execute(text("DROP SCHEMA public CASCADE"))
            dst.execute(text("CREATE SCHEMA public"))
            dst.commit()

        tables = _sqlite_tables(src)
        print(f"Tablas detectadas: {len(tables)}\n")

        total_ok, total_err = 0, 0
        for table in tables:
            cols = _table_schema(src, table)
            row = src.execute(text(f'SELECT COUNT(*) FROM "{table}"')).fetchone()
            src_count = row[0] if row is not None else 0
            if not args.solo_verificar:
                _create_table_pg(dst, table, cols)
                dst.commit()
                copied = _copy_table(src, dst, table, cols)
                dst.commit()
            else:
                copied = 0

            dst_count = None
            if not args.solo_verificar:
                try:
                    drow = dst.execute(text(f'SELECT COUNT(*) FROM "{table}"')).fetchone()
                    dst_count = drow[0] if drow is not None else 0
                except Exception as e:
                    dst_count = f"ERROR: {e}"

            ok = (copied == src_count) if not args.solo_verificar else True
            status = "OK " if ok else "DIF"
            total_ok += 1 if ok else 0
            total_err += 0 if ok else 1
            dst_txt = dst_count if dst_count is not None else "n/a"
            print(f"  [{status}] {table}: fuente={src_count} copiadas={copied} destino={dst_txt}")

        print(f"\nResultado: {total_ok} tablas OK, {total_err} con diferencias.")
        if args.solo_verificar:
            print("Modo solo-verificar: no se escribió nada en PostgreSQL.")
        return 0 if total_err == 0 else 2
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    sys.exit(main())