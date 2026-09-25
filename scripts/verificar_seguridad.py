"""Verificación de seguridad de la BD de producción (solo lectura).

Detecta desviaciones del esquema de cuentas objetivo:
- Cuentas test_* activas (deben estar bloqueadas)
- Cuentas legacy activas (deben estar bloqueadas)
- Usuarios sin rol o con rol inválido
- Admin sin forzar cambio de clave

Uso: python scripts/verificar_seguridad.py
Exit code 0 = OK, 1 = desviaciones encontradas.
"""

import sys
from datetime import datetime
from pathlib import Path

# Añadir la raíz del proyecto al path (scripts/ está un nivel dentro)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.session import SessionLocal
from src.modules.usuarios.models.usuario_model import Usuario
from src.modules.usuarios.models.rol_model import Rol  # noqa: F401  (requerido por el mapper)
from src.modules.usuarios.services.auth_service import AuthService


def main() -> int:
    problemas: list[str] = []
    session = SessionLocal()
    try:
        usuarios = session.query(Usuario).all()
        for u in usuarios:
            bloqueada = AuthService.is_account_locked(u)
            if u.username.startswith("test_"):
                if not bloqueada:
                    problemas.append(f"Cuenta test_* NO bloqueada: {u.username}")
            if u.username == "Usuario 1":
                if not bloqueada:
                    problemas.append(f"Cuenta legacy NO bloqueada: {u.username}")
            if u.rol_id not in (1, 2, 3):
                problemas.append(f"Usuario sin rol válido: {u.username} (rol_id={u.rol_id})")
            if u.username == "admin" and not u.requires_password_change:
                problemas.append("Admin NO tiene requires_password_change (debe rotar clave)")

        # Verificación objetivo: cuentas por rol
        usernames = {u.username for u in usuarios}
        for esperada in ("admin", "gerencia", "operador"):
            if esperada not in usernames:
                problemas.append(f"Falta cuenta objetivo: {esperada}")

        if problemas:
            print("SEGURIDAD: DESVIACIONES ENCONTRADAS")
            for p in problemas:
                print(f"  ✗ {p}")
            return 1
        print("SEGURIDAD: OK — esquema de cuentas correcto")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())