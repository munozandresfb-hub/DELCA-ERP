# DELCA ERP — Stack Tecnológico

## Resumen

| Atributo | Valor |
|---|---|
| Lenguaje | Python 3.13+ (runtime 3.14.5) |
| GUI | PySide6 6.11.1 (Qt for Python) |
| ORM | SQLAlchemy 2.0.51 |
| Base de Datos | SQLite 3 (WAL mode) |
| Autenticación | bcrypt 5.0.0 + SHA-256 |
| Build | PyInstaller 6.21.0 |
| Patrón | MVVM (Model-View-ViewModel) |

## Lenguaje

**Python 3.13+** (comprobado: 3.14.5 en tiempo de ejecución).

Razón: Amplio ecosistema, tipado progresivo con type hints, madurez en
aplicaciones de escritorio vía Qt, facilidad de distribución con PyInstaller.

## GUI Framework

**PySide6 6.11.1** — Binding oficial de Qt para Python.

- Qt6 Widgets para todas las vistas (sin QML).
- shiboken6 para la interoperabilidad Python/C++.
- QStackedWidget para navegación tipo página con QListWidget como sidebar.
- Sin dependencias web ni servidor HTTP.

Razón: Única opción madura para aplicaciones de escritorio nativas en Python
con widgets ricos (tablas, formularios, pestañas). Portabilidad Windows/Linux
sin cambios.

## ORM

**SQLAlchemy 2.0.51** — ORM maduro con soporte declarativo.

Estilo híbrido:
- Modelos legacy: `Cliente`, `Llanta`, `EstadoLlanta`, `UbicacionLlanta` usan
  `Column()` clásico.
- Modelos Mapped: `Rol`, `Usuario`, `Factura`, `Pago`, `Producto`,
  `MovimientoInventario`, `Auditoria`, `ReglaAutomatizacion`, `Alerta` usan
  `Mapped[]` moderno.

Patrón de sesión:
- `DeclarativeBase` como clase base única en `src/database/base.py`.
- Engine con `echo=True` (activo, debe desactivarse en producción).
- `sessionmaker` con `expire_on_commit=False` para evitar
  `DetachedInstanceError` post-commit.
- Context manager `get_session()` con commit automático en éxito,
  rollback en excepción, close en finally.
- `check_same_thread=False` para compatibilidad con hilos de Qt.

Razón: ORM maduro, consultas expresivas, transacciones explícitas, no requiere
server de BD.

## Base de Datos

**SQLite 3** — Archivo único `delca.db`.

Configuración por conexión (vía event listener `@event.listens_for(engine, "connect")`):
- `PRAGMA journal_mode=WAL` — Modo Write-Ahead Log para lectura concurrente.
- `PRAGMA foreign_keys=ON` — Integridad referencial forzada.
- `PRAGMA busy_timeout=5000` — Espera 5s antes de rendirse en bloqueo.

Razón: Cero configuración, cero servidores, backup copiando un archivo.
WAL permite lecturas durante escrituras sin bloqueos.

## Autenticación

**bcrypt 5.0.0** + **SHA-256** (pre-hash).

Flujo:
1. Entrada: contraseña en texto plano.
2. SHA-256 pre-hash (para manejar longitudes arbitrarias).
3. bcrypt.gensalt() + hashpw.
4. Almacenamiento: string VARCHAR(255) en `usuarios.password_hash`.

Verificación:
1. Recuperar hash almacenado.
2. `bcrypt.checkpw(password.encode(), hash_almacenado.encode())`.

Bootstrap:
- Primera ejecución crea rol `ADMIN` y usuario `admin`/`admin123`.

Razón: bcrypt es resistant a ataques de fuerza bruta por su costo
configurable. SHA-256 pre-hash evita truncamiento silencioso.

## Build

**PyInstaller 6.21.0** — Empaquetado en un solo EXE.

- Modo `--windowed`: sin consola (GUI pura).
- Hidden imports para los 13 modelos SQLAlchemy y servicios.
- Output: `dist/DELCA ERP.exe` (~53 MB).
- Spec file: `build_exe.spec` con exclusiones para librerías no usadas
  (tkinter, matplotlib, numpy, pandas, scipy, etc.).

Razón: Distribución autónoma sin requerir Python instalado.

## Dependencias

### Producción (requirements.txt)

| Paquete | Versión | Propósito |
|---|---|---|
| PySide6 | ==6.11.1 | GUI Qt6 |
| SQLAlchemy | ==2.0.51 | ORM |
| bcrypt | ==5.0.0 | Hashing de contraseñas |

### Build (instalado aparte)

| Paquete | Versión | Propósito |
|---|---|---|
| pyinstaller | 6.21.0 | Empaquetado EXE |
| pyinstaller-hooks-contrib | 2026.6 | Hooks para PySide6+SQLAlchemy |

## Patrón MVVM

```
┌──────────────────────────────────────────────────────┐
│                       main.py                        │
│  init_db → bootstrap_admin → init_rules → QtApp      │
└──────────┬───────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────┐
│              MainWindow (QMainWindow)                 │
│  Sidebar (QListWidget) + Stack (QStackedWidget)      │
└──────────┬───────────────────────────────────────────┘
           │ inyecta
┌──────────▼──────────┐   ┌──────────────────────────┐
│     Views (V)       │──►│    ViewModel / Service   │
│  PySide6 Widgets    │   │  (VM)                    │
│  clientes_view.py   │   │  cliente_viewmodel.py   │
│  facturacion_view   │   │  cliente_service.py     │
│  etc.               │   │  factura_service.py     │
└─────────────────────┘   └──────────┬───────────────┘
                                     │
                      ┌──────────────▼───────────────┐
                      │    Models (M)                │
                      │  SQLAlchemy ORM              │
                      │  + engine.py (SQLite)        │
                      └──────────────────────────────┘
```

**Capas por módulo:**
- **Models**: Definiciones ORM, herencia de `Base`, solo columnas y relaciones.
- **Services**: Lógica de negocio, sesiones BD, métodos estáticos.
- **ViewModels** (donde existen): Transformación de datos para la vista.
  Solo `ClienteViewModel` y `LlantaViewModel` implementan este patrón.
- **Views**: Widgets PySide6, construcción de UI, conexión de señales.
- **Repositories**: Solo `ClienteRepository` encapsula consultas CRUD.

## Decisiones Arquitectónicas Clave

1. **SQLite monolitico**: Sin servidor, backup simple, ideal para
   implementaciones de una sola oficina/taller.

2. **WAL + busy_timeout**: Previene "database is locked" en acceso concurrente
   desde Qt (múltiples hilos/widgets).

3. **expire_on_commit=False**: Esencial para que los objetos obtenidos en una
   sesión sigan funcionando después del commit. Sin esto,
   `DetachedInstanceError` rompe la UI.

4. **Inline import de AutomatizacionService**: Se importa después de
   `bootstrap_admin()` en `main.py` para evitar import circular al cargar
   modelos de otros módulos (Producto, Factura, Llanta).

5. **Numeración FAC por ID descendente**: Se reemplazó `func.max(text)` por
   `order_by(Factura.id.desc()).first()` para evitar bug de ordenamiento
   lexicográfico (FAC-10 < FAC-2 en texto).

6. **echo=True en engine**: Actualmente activo. Debe desactivarse
   (`echo=False`) en producción para no exponer SQL en consola ni llenar logs.
