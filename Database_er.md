# DELCA ERP — Esquema de Base de Datos

## Resumen

13 tablas SQLite gestionadas por SQLAlchemy 2.0.
Motor: SQLite 3 con WAL mode, foreign_keys=ON, busy_timeout=5000.

## Convenciones

- **PK**: `id INTEGER PRIMARY KEY AUTOINCREMENT` en todas las tablas.
- **Timestamps**: `datetime` naive (sin timezone), default `datetime.now` o `datetime.utcnow`.
- **Moneda/Cantidad**: `Numeric(12, 2)` para precisión decimal.
- **JSON**: Almacenado como `TEXT` (no JSON nativo de SQLite).
- **Naming**: Tablas en plural snake_case (`estados_llanta`), columnas en singular snake_case (`cliente_id`).
- **Cascades**: No definidas a nivel BD (gestión vía aplicación).
- **Índices**: Solo PKs y UNIQUE explícitos; sin índices secundarios adicionales.

## Diagrama Entidad-Relación (ASCII)

```
┌──────────────┐       ┌──────────────────┐
│    roles     │       │    usuarios      │
│──────────────│       │──────────────────│
│ id PK        │──┐    │ id PK            │
│ nombre UNIQUE│  │    │ nombre           │
└──────────────┘  │    │ username UNIQUE  │
                  │    │ password_hash    │
                  └────│ rol_id FK ───────┘
                       └────────┬─────────┘
                                │
                                │ 1
                                │
                    ┌───────────┴──────────────┐
                    │                          │
              ┌─────▼──────┐          ┌────────▼──────────┐
              │  auditoria │          │movimientos_invent.│
              │────────────│          │───────────────────│
              │ id PK      │          │ id PK             │
              │ usuario_id │          │ producto_id FK    │
              │ entidad    │          │ tipo              │
              │ accion     │          │ cantidad          │
              │ detalle    │          │ costo_unitario    │
              │ payload_js │          │ referencia        │
              │ ip_origen  │          │ observaciones     │
              │ fecha      │          │ fecha             │
              └────────────┘          │ usuario_id FK ────┘
                                     └────────────────────┘

┌──────────────┐       ┌──────────────────┐
│   cliente    │       │    llantas       │
│──────────────│       │──────────────────│
│ id PK INDEX  │──┐    │ id PK INDEX      │
│ nombre NOT   │  │    │ codigo UNIQUE    │
│ nit UNIQUE   │  │    │ marca            │
│ telefono     │  │    │ medida           │
│ celular      │  │    │ estado           │
│ email        │  │    │ cliente_id FK ───┘
│ direccion    │  ├────┘
│ ciudad       │  │
│ saldo        │  │    ┌──────────────────┐
│ activo       │  │    │ estados_llanta   │
│ categoria_ab │  │    │──────────────────│
└──────────────┘  │    │ id PK INDEX      │
                  │    │ llanta_id FK     │
┌──────────────┐  │    │ estado           │
│   facturas   │  │    │ fecha            │
│──────────────│  │    └──────────────────┘
│ id PK        │  │
│ cliente_id FK├──┘    ┌──────────────────┐
│ numero UNIQUE│       │ubicaciones_llanta│
│ fecha_emision│       │──────────────────│
│ total        │       │ id PK INDEX      │
│ saldo        │       │ llanta_id FK     │
│ estado       │       │ ubicacion        │
│ observaciones│       │ fecha            │
│ created_at   │       └──────────────────┘
└──────┬───────┘
       │
       │ 1
       │
┌──────▼───────┐
│    pagos     │
│──────────────│
│ id PK        │
│ factura_id FK│
│ valor        │
│ metodo_pago  │
│ referencia   │
│ fecha        │
│ created_at   │
└──────────────┘

┌──────────────┐       ┌──────────────────────┐
│  productos   │       │ movimientos_invent.  │
│──────────────│       │──────────────────────│
│ id PK        │──┐    │ id PK                │
│ nombre NOT   │  │    │ producto_id FK ──────┘
│ sku UNIQUE   │  │    │ tipo (ENUM string)   │
│ descripcion  │  │    │ cantidad             │
│ categoria    │  │    │ costo_unitario       │
│ stock        │  │    │ referencia           │
│ costo_unit   │  │    │ observaciones        │
│ precio_venta │  │    │ fecha                │
│ unidad_medida│  │    │ usuario_id FK (N)    │
│ activo       │  │    └──────────────────────┘
└──────────────┘  │
                  │
┌───────────────────────────────────────┐
│  reglas_automatizacion    │  alertas  │
│──────────────────────────│───────────│
│ id PK                    │ id PK     │
│ nombre NOT               │ tipo      │
│ tipo NOT                 │ mensaje   │
│ nivel (INFO/WARN/CRIT)   │ nivel     │
│ activa BOOL              │ leida BOOL│
│ config_json TEXT         │ entidad_t │
│ created_at               │ entidad_i │
└──────────────────────────│ created_at│
                           └───────────┘
```

## Tablas Detalladas

### roles

Propósito: Roles de usuario del sistema.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| nombre | VARCHAR(50) | UNIQUE, NOT NULL | |

FK: No tiene. Referenciado por `usuarios.rol_id`.

### usuarios

Propósito: Usuarios del sistema con credenciales.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| nombre | VARCHAR(100) | NOT NULL | |
| username | VARCHAR(50) | UNIQUE, NOT NULL | |
| password_hash | VARCHAR(255) | NOT NULL | |
| rol_id | INTEGER | FK → roles.id, NOT NULL | |

FK: `rol_id → roles.id`. Referenciado por `movimientos_inventario.usuario_id`, `auditoria.usuario_id`.

### cliente

Propósito: Clientes registrados en el sistema.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT, INDEX | |
| nombre | VARCHAR | NOT NULL | |
| nit | VARCHAR | UNIQUE, NOT NULL | |
| telefono | VARCHAR | nullable | NULL |
| celular | VARCHAR | nullable | NULL |
| email | VARCHAR | nullable | NULL |
| direccion | TEXT | nullable | NULL |
| ciudad | VARCHAR | nullable | NULL |
| saldo | NUMERIC | | 0 |
| activo | BOOLEAN | | True |
| categoria_abc | VARCHAR(1) | | 'B' |

FK: No tiene. Referencia a `llantas.cliente_id`, `facturas.cliente_id`.
Estilo: Legacy Column (no Mapped).

### llantas

Propósito: Registro de llantas con trazabilidad.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT, INDEX | |
| tiquete | VARCHAR(100) | UNIQUE, NOT NULL, INDEX | |
| marca | VARCHAR(100) | nullable | NULL |
| dimension | VARCHAR(100) | nullable | NULL |
| estado | VARCHAR(30) | CHECK IN (PENDIENTE, APTA, RECHAZADA, REENCAUCHADA, REPARADA, REPROCESO) | 'PENDIENTE' |
| ubicacion_actual | VARCHAR(50) | nullable | 'PLANTA' |
| cliente_id | INTEGER | FK → cliente.id | |

FK: `cliente_id → cliente.id` (lazy='joined').
Referencia a: `estados_llanta.llanta_id`, `ubicaciones_llanta.llanta_id`.
Estilo: Mapped (moderno).

**Máquina de estados:** PENDIENTE → APTA → REENCAUCHADA/REPARADA; APTA → REPROCESO → REENCAUCHADA/REPARADA/RECHAZADA. Ubicaciones: PRODUCCION, PLANTA, CLIENTE.

### estados_llanta

Propósito: Historial de cambios de estado de cada llanta.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT, INDEX | |
| llanta_id | INTEGER | FK → llantas.id, NOT NULL | |
| estado | VARCHAR | NOT NULL | |
| fecha | DATETIME | | datetime.utcnow |

FK: `llanta_id → llantas.id`.

### ubicaciones_llanta

Propósito: Historial de ubicaciones físicas de cada llanta.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT, INDEX | |
| llanta_id | INTEGER | FK → llantas.id, NOT NULL | |
| ubicacion | VARCHAR | NOT NULL | |
| fecha | DATETIME | | datetime.utcnow |

FK: `llanta_id → llantas.id`.

### facturas

Propósito: Facturas emitidas a clientes.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| cliente_id | INTEGER | FK → cliente.id, NOT NULL | |
| numero | VARCHAR(50) | UNIQUE, NOT NULL | |
| fecha_emision | DATETIME | | datetime.now |
| total | NUMERIC(12,2) | | 0 |
| saldo | NUMERIC(12,2) | | 0 |
| estado | VARCHAR(20) | | 'PENDIENTE' |
| observaciones | TEXT | nullable | NULL |
| created_at | DATETIME | | datetime.now |

FK: `cliente_id → cliente.id`.
Estados: PENDIENTE, PAGADA, ANULADA.
Numeración: FAC-NNNN (auto-generada, pk id descendente).

### pagos

Propósito: Pagos registrados contra facturas.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| factura_id | INTEGER | FK → facturas.id, NOT NULL | |
| valor | NUMERIC(12,2) | NOT NULL | |
| metodo_pago | VARCHAR(30) | | 'EFECTIVO' |
| referencia | VARCHAR(100) | nullable | NULL |
| fecha | DATETIME | | datetime.now |
| created_at | DATETIME | | datetime.now |

FK: `factura_id → facturas.id` (back_populates='pagos').
Métodos de pago: EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE, OTRO.

### productos

Propósito: Catálogo de productos de inventario (insumos, materias primas).

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| nombre | VARCHAR(150) | NOT NULL | |
| sku | VARCHAR(50) | UNIQUE, NOT NULL | |
| descripcion | VARCHAR(500) | nullable | NULL |
| categoria | VARCHAR(100) | nullable | NULL |
| stock | NUMERIC(12,2) | | 0 |
| costo_unitario | NUMERIC(12,2) | | 0 |
| precio_venta | NUMERIC(12,2) | | 0 |
| unidad_medida | VARCHAR(20) | | 'UNIDAD' |
| activo | BOOLEAN | | True |

Categorías del sistema: MATERIA_PRIMA, INSUMOS, HERRAMIENTAS, REPUESTOS, EMPAQUES, OTROS.

### movimientos_inventario

Propósito: Kardex de movimientos de inventario.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| producto_id | INTEGER | FK → productos.id, NOT NULL | |
| tipo | VARCHAR(20) | NOT NULL | |
| cantidad | NUMERIC(12,2) | NOT NULL | |
| costo_unitario | NUMERIC(12,2) | | 0 |
| referencia | VARCHAR(200) | nullable | NULL |
| observaciones | VARCHAR(500) | nullable | NULL |
| fecha | DATETIME | | datetime.now |
| usuario_id | INTEGER | FK → usuarios.id | NULL |

FK: `producto_id → productos.id`, `usuario_id → usuarios.id`.
Tipos: ENTRADA, SALIDA, MERMA, AJUSTE.

### auditoria

Propósito: Registro de cambios y actividad del sistema.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| usuario_id | INTEGER | FK → usuarios.id | NULL |
| entidad | VARCHAR(100) | NOT NULL | |
| accion | VARCHAR(20) | NOT NULL | |
| detalle | TEXT | nullable | NULL |
| payload_json | TEXT | nullable | NULL |
| ip_origen | VARCHAR(50) | nullable | NULL |
| fecha | DATETIME | | datetime.now |

FK: `usuario_id → usuarios.id`.
Acciones: CREATE, UPDATE, DELETE, LOGIN, LOGOUT.

**Nota:** El modelo existe pero NO hay servicio que implemente llamadas de auditoría automáticas. No hay hooks ni decoradores. La tabla permanece vacía.

### reglas_automatizacion

Propósito: Reglas configurables para el motor de automatización.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| nombre | VARCHAR(100) | NOT NULL | |
| tipo | VARCHAR(50) | NOT NULL | |
| nivel | VARCHAR(20) | | 'WARNING' |
| activa | BOOLEAN | | True |
| config_json | TEXT | nullable | NULL |
| created_at | DATETIME | | datetime.now |

Tipos: STOCK_BAJO, CARTERA_VENCIDA, LLANTAS_LISTAS.
Niveles: INFO, WARNING, CRITICAL.

### alertas

Propósito: Alertas generadas automáticamente por las reglas.

| Columna | Tipo | Restricciones | Default |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| tipo | VARCHAR(50) | NOT NULL | |
| mensaje | VARCHAR(500) | NOT NULL | |
| nivel | VARCHAR(20) | | 'INFO' |
| leida | BOOLEAN | | False |
| entidad_tipo | VARCHAR(50) | nullable | NULL |
| entidad_id | INTEGER | nullable | NULL |
| created_at | DATETIME | | datetime.now |

## Notas de Diseño

- **ORM híbrido**: 4 tablas legacy Column + 9 tablas Mapped moderno.
- **Sin timezone**: Todos los timestamps son naive datetime. La zona horaria es local del servidor.
- **JSON como TEXT**: `config_json` almacena JSON serializado. No se usa JSON nativo de SQLite por portabilidad.
- **Sin CASCADE**: Las eliminaciones se gestionan desde la capa de aplicación, no desde la BD. Esto permite validación previa.
- **Sin índices secundarios**: Las consultas se apoyan en PKs y UNIQUEs. Módulos pequeños (<5000 registros esperados) no requieren optimización.
