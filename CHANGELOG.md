# Changelog — DELCA ERP

Todas las modificaciones significativas de este proyecto se documentan aquí.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-06-24 — Hardening de Producción

### Added (Nuevas Funcionalidades)

#### Backup & Recovery
- `src/core/services/backup_service.py`: Sistema completo de backup/restore
- `src/core/views/backup_view.py`: Interfaz de 3 tabs (Backup/Restore, Exportar, Recuperación)
- Backup automático con `wal_checkpoint(TRUNCATE)` antes de copia
- Restauración segura: renombra DB actual a `.bak` como safety net
- Exportación CSV (UTF-8 BOM) y XLSX (openpyxl) para las 13 tablas
- Verificación de integridad SQLite (PRAGMA integrity_check)
- Retención de 30 backups con pruning automático
- `was_backup_done_today()` para control diario

#### Seguridad — Autenticación
- Política de contraseñas: 8+ caracteres, mayúscula, minúscula, dígito, especial
- Expiración de contraseña a los 90 días
- Bloqueo de cuenta tras 5 intentos fallidos (15 minutos)
- Forzar cambio de contraseña en primer login (`requires_password_change`)
- Registro de `failed_attempts` y `locked_until` en usuario
- `PasswordChangeDialog` en login_window para cambio forzado

#### Seguridad — RBAC
- `permiso_model.py`: Modelo Permiso + tabla asociativa roles_permisos
- `permiso_service.py`: Servicio de verificación con caché LRU
- `bootstrap_rbac.py`: 26 permisos en 12 módulos + 4 roles predefinidos
- Sidebar filtrado por permisos en MainWindow
- Funciones: `tiene_permiso()`, `tiene_permiso_por_usuario()`, `permisos_de_rol()`
- Clase `Perms` con constantes tipadas para todos los códigos de permiso

#### Seguridad — Sesión
- `session_service.py`: SessionManager singleton con timeout de inactividad (30 min)
- `eventFilter` en MainWindow para detectar actividad (mouse, teclado)
- Timer de verificación cada 30s
- Tracking de login time y duración de sesión

#### Auditoría
- `audit_service.py`: Servicio de auditoría con funciones especializadas
- `registrar_login()` / `registrar_logout()` para eventos de autenticación
- `registrar_crud()` para operaciones CREATE/UPDATE/DELETE
- `registrar_cambio_password()` para cambios de contraseña
- Integración con login_user (LOGIN exitoso, FALLO_LOGIN)
- Integración con session_service (LOGOUT al cerrar sesión)

#### Testing
- Suite completa de 47 tests con pytest
- `tests/conftest.py`: Fixtures con BD en memoria (SQLite :memory:)
- `test_auth_service.py`: 18 tests — password policy, hashing, expiry, lockout
- `test_session_service.py`: 9 tests — singleton, actividad, timeout, lock/unlock
- `test_audit_service.py`: 8 tests — auditoría, login/logout, CRUD
- `test_permiso_service.py`: 6 tests — permisos, roles, caching
- `test_backup_service.py`: 5 tests — backup, listado, integridad
- pytest-cov instalado para medición de cobertura

#### Documentación Técnica
- `Stack.md`: Stack tecnológico completo (Python 3.13+, PySide6, SQLAlchemy 2.0, etc.)
- `Database_er.md`: Diagrama ER de las 13 tablas con relaciones
- `project_structure.md`: Árbol completo, convenciones y dependencias
- `business_rules.md`: Reglas de negocio de los 8 módulos funcionales
- `production_readiness_report.md`: Evaluación completa con score 58→94/100
#### Configuración Centralizada (Wave 5a)
- `src/config.py`: Settings class con variables de entorno
- `.env`: Archivo de configuración con DATABASE_URL, LOG_DIR, BACKUP_DIR, DATA_DIR
- `.env.example`: Template documentado de configuración
- `engine.py`: Refactorizado para usar `src.config.settings`
- `backup_service.py`: Refactorizado para usar `settings.BACKUP_DIR`
- Soporte futuro PostgreSQL vía DATABASE_URL en .env
- `python-dotenv` 1.2.2 instalado

#### Gestión de Usuarios UI (Wave 5b)
- `src/modules/usuarios/services/usuario_service.py`: CRUD completo de usuarios
- `src/modules/usuarios/views/usuarios_view.py`: UI con tabla, búsqueda, CRUD
  - UsuarioFormDialog: crear/editar usuario con selección de rol
  - PasswordResetDialog: reset de contraseña con validación
  - Desactivar usuario (limpia password hash)
- `main_window.py`: Módulo Usuarios agregado al sidebar (permiso `usuarios.gestionar`)
- Auditoría integrada en todas las operaciones (CREATE/UPDATE/DELETE)

#### Instalador Profesional (Wave 5c)
- `installer.iss`: Script Inno Setup para instalador Windows
  - Instalación guiada (WizardStyle modern)
  - Directorio en Program Files
  - Carpetas data/ backups/ logs/ creadas automáticamente
  - Acceso directo en Escritorio (opcional)
  - Menú Inicio + desinstalador
  - .env generado automáticamente apuntando a {app}\data\delca.db
  - Soporte español + inglés
- `BUILD.md`: Instrucciones para compilar EXE e instalador

### Changed (Cambios)

#### DB Engine
- `engine.py`: `echo=True` → `echo=False` (seguridad en producción)
- `engine.py`: Rotating file logging a `logs/delca.log` (5 MB, 3 backups)
- Loggers SQLAlchemy silenciados a WARNING

#### DB Hardening — Modelos
- `cliente_model.py`: Relaciones facturas/llantas con back_populates; nit index; String(1) fix
- `factura_model.py`: CheckConstraint estado, índices, ondelete="RESTRICT", cascade pagos
- `pago_model.py`: CheckConstraint metodo_pago, ondelete="CASCADE", índice
- `llanta_model.py`: CheckConstraint estado, cascade delete-orphan, ondelete="RESTRICT"
- `estado_llanta_model.py`: CheckConstraint, ondelete="CASCADE", índice
- `ubicacion_llanta_model.py`: ondelete="CASCADE", índice
- `movimiento_inventario_model.py`: CheckConstraint tipo, ondelete="CASCADE"/"SET NULL", índices
- `producto_model.py`: CheckConstraint unidad_medida, cascade, back_populates
- `auditoria_model.py`: CheckConstraint accion, ondelete="SET NULL", índices
- `rol_model.py`: Relación usuarios con back_populates
- `usuario_model.py`: Relación rol con back_populates; columnas de seguridad
- `regla_model.py`: CheckConstraints para tipo y nivel, índices
- `alerta_model.py`: CheckConstraints para nivel, índices

#### Login Flow
- `login_user.py`: Verificación de bloqueo, registro de intentos, auditoría LOGIN/FALLO_LOGIN
- `login_window.py`: PasswordChangeDialog, flujo de cambio forzado
- `login_viewmodel.py`: Método change_password() con auditoría

#### Bootstrap
- `bootstrap_admin.py`: Crea 4 roles (ADMIN, GERENCIA, OPERADOR, CONSULTA), llama bootstrap_rbac()
- Admin user creado con `requires_password_change=True`

### Removed (Eliminaciones)
- `Cliente.categoria_abc`: Type annotation incorrecta `Column[str]` → corregida a `Column(String)`

### Fixed
- DB path relativo: Ahora configurable via `.env` (DATABASE_URL, LOG_DIR, BACKUP_DIR)
- Gestión de usuarios desde UI: Implementada (listar, crear, editar, desactivar, reset password)

### Known Issues
- openpyxl: No incluido en el build de PyInstaller (necesario para exportación Excel)
- Login del viewmodel: El `change_password` usa su propia sesión, no la del test
- Scheduler automático de backup: No implementado (backup manual via UI)

---

## [0.1.0] — 2026-06-xx — Versión Inicial

Sistema ERP funcional con 8 módulos de negocio.
- Autenticación básica con bcrypt
- 13 tablas en SQLite
- 12 vistas funcionales en sidebar
- EXE compilado con PyInstaller
