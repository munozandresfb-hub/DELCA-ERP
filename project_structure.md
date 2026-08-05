# DELCA ERP — Estructura del Proyecto

## Árbol de Directorios

```
Programacion DELCA/
│
├── main.py                      # Entry point. Crea tablas, bootstrap admin,
│                                # init reglas, lanza LoginWindow via QApplication.
│
├── requirements.txt             # Producción: PySide6, SQLAlchemy, bcrypt.
├── build_exe.spec               # PyInstaller spec (EXE sin consola, hidden imports).
├── delca.db                     # BD SQLite (auto-creada en primera ejecución).
├── delca.db-wal                 # WAL file de SQLite (registro de escritura).
├── delca.db-shm                 # Shared memory file de SQLite WAL.
│
├── logs/                        # Directorio para logs (actualmente vacío).
├── backups/                     # Directorio para backups (actualmente vacío).
├── resources/                   # Recursos estáticos (iconos, etc.).
├── tests/                       # Directorio de pruebas (actualmente vacío).
├── .venv/                       # Entorno virtual Python.
│
├── dist/                        # Output de PyInstaller.
│   └── DELCA ERP.exe            # Ejecutable autónomo (~53 MB).
│
├── build/                       # Artefactos de compilación PyInstaller.
│
├── README.md                    # Documentación principal.
├── Stack.md                     # Documentación del stack tecnológico.
├── Database_er.md               # Documentación del esquema de BD.
├── project_structure.md         # Este archivo.
├── business_rules.md            # Documentación de reglas de negocio.
│
└── src/
    ├── __init__.py
    │
    ├── database/
    │   ├── __init__.py
    │   ├── base.py              # DeclarativeBase de SQLAlchemy.
    │   └── engine.py            # Engine, sessionmaker (expire_on_commit=False),
    │                             # get_session() context manager, WAL mode.
    │
    ├── core/
    │   ├── __init__.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── dashboard_service.py  # KPIs: conteos, métricas financieras,
    │   │                             # actividad reciente, llantas por estado.
    │   └── views/
    │       ├── __init__.py
    │       ├── main_window.py        # QMainWindow: sidebar 11 items +
    │       │                         # QStackedWidget.
    │       └── dashboard_view.py     # Dashboard con tarjetas KPI, badges de
    │                                 # estados, feed de actividad.
    │
    ├── ui/
    │   └── __init__.py              # Componentes UI reutilizables (vacío).
    │
    └── modules/
        ├── __init__.py
        │
        ├── usuarios/                # ─── Módulo de Usuarios ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   ├── rol_model.py        # Rol: id, nombre (unique).
        │   │   └── usuario_model.py    # Usuario: nombre, username (unique),
        │   │                           #   password_hash, rol_id FK.
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── auth_service.py     # hash_password(), verify_password().
        │   ├── use_cases/
        │   │   ├── __init__.py
        │   │   └── bootstrap_admin.py  # Creación inicial de rol ADMIN + admin.
        │   └── views/
        │       ├── __init__.py
        │       └── login_window.py     # QDialog login con username + password.
        │
        ├── clientes/                # ─── Módulo de Clientes ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   └── cliente_model.py    # Cliente (11 cols, legacy Column).
        │   ├── repositories/
        │   │   ├── __init__.py
        │   │   └── cliente_repository.py  # Único repositorio del sistema.
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── cliente_service.py     # CRUD, búsqueda, clasificación ABC.
        │   ├── viewmodels/
        │   │   ├── __init__.py
        │   │   └── cliente_viewmodel.py   # Transformación datos para tabla.
        │   └── views/
        │       ├── __init__.py
        │       └── clientes_view.py       # Tabla CRUD con búsqueda.
        │
        ├── llantas/                 # ─── Módulo de Llantas ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   ├── llanta_model.py          # Llanta (6 cols, legacy Column).
        │   │   ├── estado_llanta_model.py   # EstadoLlanta (historial).
        │   │   └── ubicacion_llanta_model.py # UbicacionLlanta (historial).
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── llanta_service.py        # Registro, transición estados.
        │   ├── viewmodels/
        │   │   ├── __init__.py
        │   │   └── llanta_viewmodel.py      # Lógica de máquina de estados.
        │   └── views/
        │       ├── __init__.py
        │       ├── llantas_view.py          # Registro con filtro por estado.
        │       ├── produccion_view.py       # Pipeline de producción (llantas activas).
        │       └── planta_view.py           # Mapa de planta/ubicaciones.
        │
        ├── finanzas/                # ─── Módulo de Finanzas ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   ├── factura_model.py    # Factura (9 cols, Mapped).
        │   │   └── pago_model.py       # Pago (7 cols, Mapped).
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── factura_service.py  # Numeración, CRUD, pagos, anulación,
        │   │                           #   reporte de antigüedad.
        │   └── views/
        │       ├── __init__.py
        │       ├── facturacion_view.py  # Creación de facturas + pagos.
        │       └── cartera_view.py      # Cartera con antigüedad coloreada.
        │
        ├── inventario/              # ─── Módulo de Inventario ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   ├── producto_model.py         # Producto (10 cols, Mapped).
        │   │   └── movimiento_inventario_model.py  # Movimiento (9 cols).
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── producto_service.py   # CRUD, movimientos, kardex, resúmenes.
        │   └── views/
        │       ├── __init__.py
        │       ├── productos_view.py     # CRUD de productos.
        │       └── kardex_view.py        # Historial de movimientos coloreado.
        │
        ├── reportes/                # ─── Módulo de Reportes ───
        │   ├── __init__.py
        │   ├── services/
        │   │   ├── __init__.py
        │   │   └── reporte_service.py     # Consultas multi-módulo agregadas.
        │   └── views/
        │       ├── __init__.py
        │       └── reportes_view.py       # 5 tabs: clientes, llantas, finanzas,
        │                                 #   inventario, resumen general.
        │
        ├── auditoria/               # ─── Módulo de Auditoría ───
        │   ├── __init__.py
        │   ├── models/
        │   │   ├── __init__.py
        │   │   └── auditoria_model.py   # Auditoria (8 cols, Mapped).
        │   ├── services/
        │   │   └── __init__.py          # Sin implementación de servicio.
        │   └── views/
        │       └── __init__.py          # Sin vista en sidebar.
        │
        └── automatizacion/          # ─── Módulo de Automatización ───
            ├── __init__.py
            ├── models/
            │   ├── __init__.py
            │   └── regla_model.py       # ReglaAutomatizacion + Alerta.
            ├── services/
            │   ├── __init__.py
            │   └── automatizacion_service.py  # Evaluación de reglas,
            │                                 #   alertas, deduplicación.
            └── views/
                ├── __init__.py
                └── automatizacion_view.py     # 3 tabs: alertas activas,
                                              #   configuración, historial.
```

## Convenciones de Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos .py | snake_case | `cliente_model.py`, `factura_service.py` |
| Clases | PascalCase | `Cliente`, `FacturaService` |
| Funciones/métodos | snake_case | `registrar_movimiento()` |
| Tablas BD | plural snake_case | `roles`, `estados_llanta` |
| Columnas BD | singular snake_case | `cliente_id`, `fecha_emision` |
| Sidebar labels | Title Case | "Dashboard", "Automatización" |
| Variables | snake_case | `total_pendiente` |

## Reglas de Límites entre Módulos

1. **Models**: Solo definiciones ORM. Sin lógica de negocio.
2. **Services**: Lógica de negocio, métodos estáticos, sesiones BD via `get_session()`.
3. **Views**: Widgets PySide6, construcción de UI, conexión de señales.
4. **ViewModels** (donde existen): Transformación datos entre service y view.
5. **Repositories**: Solo `ClienteRepository`. El resto accede BD directamente.
6. **No imports cruzados views→services**: Views importan services, no al revés.
7. **Services pueden importar models de otros módulos**: Ej: AutomatizacionService
   importa Producto, Factura, Llanta.
8. **main.py importa todos los models antes de create_all()**: Para que SQLAlchemy
   los registre con Base.

## Mapa de Dependencias entre Módulos

```
main.py
├── src.database.base         (Base)
├── src.database.engine       (engine, get_session)
├── src.modules.usuarios.*    (13 models: Rol..Alerta)
├── src.modules.usuarios.use_cases.bootstrap_admin
├── src.modules.usuarios.views.login_window
└── src.modules.automatizacion.services.automatizacion_service
    └── (import inline después de bootstrap, evita import circular)

AutomatizacionService
├── src.database.engine
├── src.modules.automatizacion.models.regla_model
├── src.modules.clientes.models.cliente_model
├── src.modules.finanzas.models.factura_model
├── src.modules.inventario.models.producto_model
└── src.modules.llantas.models.llanta_model

DashboardService
├── src.database.engine
├── src.modules.clientes.models.cliente_model
├── src.modules.finanzas.models.factura_model
├── src.modules.finanzas.models.pago_model
├── src.modules.llantas.models.estado_llanta_model
├── src.modules.llantas.models.llanta_model
└── src.modules.llantas.models.ubicacion_llanta_model
```

## Vistas del Sidebar (11 items)

| Índice | Nombre | Clase | Archivo |
|---|---|---|---|
| 0 | Dashboard | DashboardView | `src/core/views/dashboard_view.py` |
| 1 | Clientes | ClientesView | `src/modules/clientes/views/clientes_view.py` |
| 2 | Llantas | LlantasView | `src/modules/llantas/views/llantas_view.py` |
| 3 | Producción | ProduccionView | `src/modules/llantas/views/produccion_view.py` |
| 4 | Planta | PlantaView | `src/modules/llantas/views/planta_view.py` |
| 5 | Facturación | FacturacionView | `src/modules/finanzas/views/facturacion_view.py` |
| 6 | Cartera | CarteraView | `src/modules/finanzas/views/cartera_view.py` |
| 7 | Inventario | ProductosView | `src/modules/inventario/views/productos_view.py` |
| 8 | Kardex | KardexView | `src/modules/inventario/views/kardex_view.py` |
| 9 | Reportes | ReportesView | `src/modules/reportes/views/reportes_view.py` |
| 10 | Automatización | AutomatizacionView | `src/modules/automatizacion/views/automatizacion_view.py` |

## Servicios (8 módulos)

| Servicio | Archivo | Responsabilidad |
|---|---|---|
| AuthService | `usuarios/services/auth_service.py` | Hash y verificación bcrypt |
| ClienteService | `clientes/services/cliente_service.py` | CRUD + búsqueda + clasificación ABC |
| LlantaService | `llantas/services/llanta_service.py` | Registro + transiciones de estado |
| FacturaService | `finanzas/services/factura_service.py` | Numeración FAC, CRUD, pagos, anulación, aging |
| ProductoService | `inventario/services/producto_service.py` | CRUD, movimientos stock, kardex, resúmenes |
| ReporteService | `reportes/services/reporte_service.py` | Reportes multi-módulo agregados |
| AutomatizacionService | `automatizacion/services/automatizacion_service.py` | Evaluación reglas, alertas, dedup |
| DashboardService | `core/services/dashboard_service.py` | KPIs, actividad reciente, llantas por estado |
