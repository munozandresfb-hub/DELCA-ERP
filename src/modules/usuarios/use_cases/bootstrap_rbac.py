"""Seed default roles and permissions for RBAC.

Run once on first deployment or whenever permissions change.
"""

from src.database.engine import SessionLocal
from src.modules.usuarios.models.permiso_model import Permiso, rol_permiso
from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.services.permiso_service import clear_permiso_cache


# ── Define all permissions ─────────────────────────────────────────────

ALL_PERMISOS: list[dict] = [
    # Dashboard
    {"codigo": "dashboard.ver", "nombre": "Ver Dashboard", "modulo": "dashboard"},
    # Clientes
    {"codigo": "clientes.ver", "nombre": "Ver clientes", "modulo": "clientes"},
    {"codigo": "clientes.crear", "nombre": "Crear clientes", "modulo": "clientes"},
    {"codigo": "clientes.editar", "nombre": "Editar clientes", "modulo": "clientes"},
    {"codigo": "clientes.eliminar", "nombre": "Eliminar clientes", "modulo": "clientes"},
    # Llantas
    {"codigo": "llantas.ver", "nombre": "Ver llantas", "modulo": "llantas"},
    {"codigo": "llantas.crear", "nombre": "Crear llantas", "modulo": "llantas"},
    {"codigo": "llantas.editar", "nombre": "Editar llantas", "modulo": "llantas"},
    {"codigo": "llantas.eliminar", "nombre": "Eliminar llantas", "modulo": "llantas"},
    # Producción
    {"codigo": "produccion.ver", "nombre": "Ver producción", "modulo": "produccion"},
    {"codigo": "produccion.gestionar", "nombre": "Gestionar producción", "modulo": "produccion"},
    # Planta
    {"codigo": "planta.ver", "nombre": "Ver planta", "modulo": "planta"},
    {"codigo": "planta.gestionar", "nombre": "Gestionar planta", "modulo": "planta"},
    # Facturación
    {"codigo": "facturacion.ver", "nombre": "Ver facturación", "modulo": "facturacion"},
    {"codigo": "facturacion.crear", "nombre": "Crear facturas", "modulo": "facturacion"},
    {"codigo": "facturacion.anular", "nombre": "Anular facturas", "modulo": "facturacion"},
    # Cartera
    {"codigo": "cartera.ver", "nombre": "Ver cartera", "modulo": "cartera"},
    {"codigo": "cartera.cobrar", "nombre": "Registrar cobros", "modulo": "cartera"},
    # Inventario
    {"codigo": "inventario.ver", "nombre": "Ver inventario", "modulo": "inventario"},
    {"codigo": "inventario.ajustar", "nombre": "Ajustar inventario", "modulo": "inventario"},
    # Kardex
    {"codigo": "kardex.ver", "nombre": "Ver kardex", "modulo": "kardex"},
    # Reportes
    {"codigo": "reportes.ver", "nombre": "Ver reportes", "modulo": "reportes"},
    # Automatización
    {"codigo": "automatizacion.ver", "nombre": "Ver automatización", "modulo": "automatizacion"},
    {"codigo": "automatizacion.gestionar", "nombre": "Gestionar reglas", "modulo": "automatizacion"},
    # Backup
    {"codigo": "backup.gestionar", "nombre": "Gestionar backups", "modulo": "backup"},
    # Usuarios
    {"codigo": "usuarios.gestionar", "nombre": "Gestionar usuarios", "modulo": "usuarios"},
    # Auditoría
    {"codigo": "auditoria.ver", "nombre": "Ver auditoría", "modulo": "auditoria"},
]

# ── Role → Permission mapping ──────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": [p["codigo"] for p in ALL_PERMISOS],
    "GERENCIA": [
        "dashboard.ver",
        "clientes.ver", "clientes.crear", "clientes.editar",
        "llantas.ver", "llantas.crear", "llantas.editar",
        "produccion.ver", "produccion.gestionar",
        "planta.ver", "planta.gestionar",
        "facturacion.ver", "facturacion.crear", "facturacion.anular",
        "cartera.ver", "cartera.cobrar",
        "inventario.ver", "inventario.ajustar",
        "kardex.ver",
        "reportes.ver",
        "automatizacion.ver", "automatizacion.gestionar",
        "auditoria.ver",
    ],
    "OPERADOR": [
        "dashboard.ver",
        "clientes.ver", "clientes.crear", "clientes.editar",
        "llantas.ver", "llantas.crear", "llantas.editar",
        "produccion.ver", "produccion.gestionar",
        "planta.ver", "planta.gestionar",
        "facturacion.ver", "facturacion.crear",
        "cartera.ver", "cartera.cobrar",
        "inventario.ver",
        "kardex.ver",
        "reportes.ver",
    ],
}


def bootstrap_rbac():
    """Seed the database with all permissions and assign them to roles.

    Idempotent: safe to run multiple times.
    """
    session = SessionLocal()
    try:
        # ── Create permissions ──────────────────────────────────────
        existing_codigos = {
            row.codigo for row in session.query(Permiso.codigo).all()
        }
        for pdata in ALL_PERMISOS:
            if pdata["codigo"] not in existing_codigos:
                permiso = Permiso(**pdata)
                session.add(permiso)
                existing_codigos.add(pdata["codigo"])
        session.commit()

        # ── Assign permissions to roles ─────────────────────────────
        # Build codigo → id map
        codigo_id = {
            row.codigo: row.id
            for row in session.query(Permiso.codigo, Permiso.id).all()
        }

        for role_name, perm_codigos in ROLE_PERMISSIONS.items():
            role = session.query(Rol).filter(Rol.nombre == role_name).first()
            if not role:
                continue  # role doesn't exist yet; bootstrap_admin creates ADMIN

            # Get current permiso ids for this role
            existing_ids = {
                row.permiso_id
                for row in session.execute(
                    rol_permiso.select().where(rol_permiso.c.rol_id == role.id)
                )
            }

            new_ids = {codigo_id[c] for c in perm_codigos if c in codigo_id}
            to_add = new_ids - existing_ids
            for pid in to_add:
                session.execute(
                    rol_permiso.insert().values(rol_id=role.id, permiso_id=pid)
                )

        session.commit()
        clear_permiso_cache()
    finally:
        session.close()
