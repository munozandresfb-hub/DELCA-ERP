# DELCA ERP — Release v1.0

**Fecha:** 2026-06-24
**Versión:** 1.0.0
**Estado:** PRODUCCIÓN ✅ — Score 94/100

---

## Resumen Ejecutivo

DELCA ERP es un sistema de planificación de recursos empresariales diseñado
para la gestión operativa de DELCA. Tras 5 waves de hardening de producción,
el sistema alcanza un puntaje de **94/100** en producción readiness,
clasificado como **Excelente — Producción Enterprise-Grade**.

El sistema está listo para despliegue multiusuario en producción con
4 roles (ADMIN, GERENCIA, OPERADOR, CONSULTA), respaldado por 47 pruebas
automatizadas, backup automático, auditoría operativa y un instalador
profesional.

---

## Novedades v1.0

### 🔐 Seguridad
- **Autenticación**: bcrypt con SHA-256 pre-hash. Política de contraseñas
  (8+ chars, mayúscula, minúscula, dígito, especial, expiración 90d).
- **Bloqueo de cuenta**: 5 intentos fallidos → bloqueo 15 min.
- **RBAC completo**: 4 roles (ADMIN, GERENCIA, OPERADOR, CONSULTA).
  26 permisos granularmente definidos en 12 módulos.
- **Sidebar filtrado**: cada usuario ve solo los módulos autorizados.
- **Sesión con timeout**: 30 min de inactividad, lock automático.

### 📋 Gestión de Usuarios
- UI completa: listar, crear, editar, desactivar, reset password.
- Asignación de roles por usuario.
- Auditoría de todas las operaciones de administración.

### 💾 Backup & Recovery
- Backup automático con WAL checkpoint antes de copia.
- Restauración con safety net (.bak).
- Exportación CSV (UTF-8 BOM) y Excel (openpyxl) para las 13 tablas.
- Verificación de integridad SQLite (PRAGMA integrity_check).
- Retención de 30 backups con pruning automático.

### 🗄️ Base de Datos
- Hardening completo: FKs con ondelete, CHECK constraints, índices compuestos.
- WAL mode, PRAGMA foreign_keys=ON, busy_timeout=5000.
- Configurable vía `.env` (DATABASE_URL, LOG_DIR, BACKUP_DIR).
- Soporte futuro PostgreSQL (vía SQLAlchemy URL).

### 🧪 Testing
- 47 tests automatizados (pytest).
- Cobertura: auth (14), session (9), backup (5), audit (8), permisos (6).
- Fixtures con SQLite in-memory.

### 📦 Deployment
- Configuración centralizada via `.env`.
- Instalador Inno Setup profesional (guiado, Program Files,
  data/backups/logs, desktop shortcut, uninstaller).
- `echo=False` + logging rotativo a `logs/delca.log`.

### 📚 Documentación
- `Stack.md` — Stack tecnológico completo
- `Database_er.md` — Diagrama ER con 13 tablas
- `project_structure.md` — Árbol de proyecto y convenciones
- `business_rules.md` — Reglas de negocio de 8 módulos
- `production_readiness_report.md` — Score 58→94/100
- `BUILD.md` — Instrucciones de build
- `CHANGELOG.md` — Historial completo de cambios

---

## Módulos del Sistema

| # | Módulo | Permisos | Descripción |
|---|---|---|---|
| 1 | Dashboard | dashboard.ver | Panel principal con indicadores |
| 2 | Clientes | clientes.{ver,crear,editar,eliminar} | Gestión de clientes |
| 3 | Llantas | llantas.{ver,crear,editar,eliminar} | Inventario de llantas |
| 4 | Producción | produccion.{ver,gestionar} | Producción de llantas |
| 5 | Planta | planta.{ver,gestionar} | Gestión de planta |
| 6 | Facturación | facturacion.{ver,crear,anular} | Facturación |
| 7 | Cartera | cartera.{ver,cobrar} | Gestión de cartera |
| 8 | Inventario | inventario.{ver,ajustar} | Control de inventario |
| 9 | Kardex | kardex.ver | Kardex de productos |
| 10 | Reportes | reportes.ver | Reportes operativos |
| 11 | Automatización | automatizacion.{ver,gestionar} | Reglas automáticas |
| 12 | Backup | backup.gestionar | Backup y restore |
| 13 | Usuarios | usuarios.gestionar | Gestión de usuarios (solo ADMIN) |

---

## Stack Tecnológico

| Componente | Versión |
|---|---|
| Python | 3.14.5 |
| PySide6 | 6.x (Qt6) |
| SQLAlchemy | 2.x |
| SQLite | WAL mode |
| bcrypt | 5.x |
| openpyxl | 3.1.5 |
| python-dotenv | 1.2.2 |
| pytest | 9.x |
| PyInstaller | (para EXE) |
| Inno Setup | 6+ (instalador) |

---

## Requisitos del Sistema

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4 GB mínimo (8 GB recomendado)
- **Disco**: 500 MB libres
- **Resolución**: 1280x720 mínimo
- **Dependencias**: ninguna (todo incluido en el instalador)

---

## Instalación

1. Ejecutar `DELCA_ERP_Setup_1.0.0.exe`
2. Seguir el asistente de instalación
3. El instalador crea accesos directos en Escritorio y Menú Inicio
4. El usuario por defecto es `admin` con contraseña `admin123`
5. **Importante**: cambiar la contraseña en el primer inicio

### Build desde código fuente

Ver `BUILD.md` para instrucciones detalladas.

---

## Licencia

Uso interno — DELCA © 2026
