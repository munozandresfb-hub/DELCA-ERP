# Changelog — DELCA ERP

Todas las modificaciones significativas de este proyecto se documentan aquí.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.8.27] — 2026-09-18 — Diseños de banda sincronizados con productos MP (Kardex automático)

### Fixed
- **Un diseño de banda nuevo no aparecía en el Kardex** (Ingreso manual): los diseños se guardan en `disenos_llanta` y el Kardex carga productos de MP — el diseño no tenía producto asociado
- **Sincronización automática**: al **crear un diseño de banda** en Catálogos → Diseños de Banda, se crea automáticamente su producto MP **"Banda {diseño}"** (SKU `BANDA{...}`, unidad ROLLO, stock 0) → queda disponible al instante en el Kardex
- **32 diseños existentes sin producto sincronizados** (`scripts/sincronizar_disenos_productos.py`, backup `delca_pre_sync_disenos_20260918_174754.db`) — verificado: no duplica los diseños que ya tienen producto (búsqueda por nombre contenido, ej. 'DVRT4' → 'Banda DVRT4 242')

### Verification
- `Banda RZE1 190` (id 98, SKU BANDARZE1190) disponible en productos MP · crear_diseno genera su producto automáticamente
- 161 tests passing · EXE recompilado

---

## [2.8.26] — 2026-09-18 — Kardex: Valor Total = costo × KG + detalle del documento al hacer clic

### Changed
- **Columna "Valor Total" del Kardex**: ahora usa la fórmula **costo unitario × cantidad de KG** (antes stock × costo) — en la tabla y en las exportaciones Excel/PDF
- **Ventana "Documentos de inventario"**: al hacer **doble clic sobre el número de documento** (entrada, salida o ajuste) se abre una nueva ventana con la **información que almacena el documento**: producto (nombre/SKU), cantidad en unidades y en KG, fecha, tipo, referencia y observaciones de cada movimiento vinculado

### Verification
- `movimientos_por_documento` devuelve los movimientos con su producto · diálogos construyen correctamente (2 movimientos → 2 filas)
- 161 tests passing · EXE recompilado

---

## [2.8.25] — 2026-09-18 — Kardex: número de documento constante entre movimientos (documentos multi-producto)

### Changed
- **N° de Factura / Documento se mantiene constante** entre movimientos del mismo tipo (ENTRADA/SALIDA): el último número usado se recuerda y se pre-rellena en el siguiente formulario, hasta que el usuario lo **cambie manualmente**
- **`crear_documento` reutiliza** el documento si el número ya existe (antes devolvía error) → un documento agrupa **varios productos** (mismo documento_id para varios movimientos)
- Verificado: 2 movimientos de productos distintos bajo el mismo documento (1 documento) · número inicial pre-rellenado

### Verification
- 161 tests passing · EXE recompilado

---

## [2.8.24] — 2026-09-18 — Kardex: Cantidad Und + Cantidad KG + Documentos de inventario

### Changed (código + datos)
- **Formularios del Kardex** (Ingreso, Salida, Ajuste): "Cantidad" → **"Cantidad Und"** + nueva casilla **"Cantidad KG"** (con auto-sugerencia según el ratio KG/und del producto). El movimiento actualiza `stock` (und) y `stock_kg`. Columna `cantidad_kg` agregada a `movimientos_inventario` (backup `delca_pre_cantidad_kg.db`)
- **Tabla Inventario (Materia Prima)**: columnas → SKU, Nombre, Categoría, **Cantidad UND** (era Stock), Unidad, **Q minima en planta** (era Mínimo), **Cantidad KG**, Costo Unit., Valor Total
- **Kardex**: columnas = inventario (SKU, Nombre, Categoría, Cantidad UND, Unidad, Q minima, Cantidad KG, Costo, Valor Total) + movimiento (Fecha, Documento de:, Cant. Und, Cant. KG, Saldo Und, Saldo KG, Referencia, Observaciones) · export Excel/PDF actualizados
- **Botón "📋 Documentos"** en el Kardex: documentos de **Ingreso** (N° de factura) y **Salida** (N° consecutivo digitado por el usuario) en `documentos_inventario` (tabla recreada con CHECK ampliado: INGRESO/SALIDA — backup `delca_pre_recrear_docs.db`). Los formularios de movimiento piden el N° de factura/documento y vinculan el movimiento al documento

### Verification
- Movimientos Und+KG: ENTRADA +2/+130.1 → stock 12 · SALIDA -3/-195 → 9 · AJUSTE → 5/300 ✓
- Documentos INGRESO/SALIDA creados y listados ✓ · stock_kg migrado del Excel verificado (44 productos con KG, suma 11,836 kg)
- 161 tests passing · EXE recompilado

---

## [2.8.23] — 2026-09-17 — Fix: botones Salida manual y Ajuste del Kardex no respondían

### Fixed
- **Bug en `_MovimientoFormDialog`**: `_cargar_productos()` se ejecutaba ANTES de crear `referencia_input`, y el autocompletado de "Unidad de medida" (SALIDA/AJUSTE) accedía a un atributo inexistente → `AttributeError` al abrir el diálogo → los botones "Salida manual" y "Ajuste" no respondían (ENTRADA funcionaba porque no usa el autocompletado)
- **Solución**: se crean todos los widgets del formulario ANTES de cargar los productos (y se conecta la señal al final). Verificado: los 3 diálogos construyen correctamente (SALIDA/AJUSTE con unidad "Rollo" autocompletada)

### Verification
- 161 tests passing · EXE recompilado

---

## [2.8.22] — 2026-09-17 — Kardex: formulario salida/ajuste simplificado + botón Merma eliminado

### Changed
- **Formulario "Registrar Salida de MP" (SALIDA)**: eliminado el campo "Costo Unit. $" (usa el costo actual del producto) · campo "Referencia" → **"Unidad de medida"** (autocompletado con la unidad del producto seleccionado)
- **Formulario "Ajustar Stock" (AJUSTE)**: queda igual que el de salida (sin costo, con "Unidad de medida")
- **Formulario "Registrar Ingreso de MP" (ENTRADA)**: conserva "Costo Unit. $" y "Referencia" (inalterado)
- **Botón "Merma" eliminado** de la barra del Kardex (el tipo MERMA sigue disponible solo para consulta de movimientos históricos)

### Verification
- 161 tests passing · EXE recompilado

---

## [2.8.21] — 2026-09-17 — Kardex: estilo de tabla igual al inventario + "Documento de:"

### Changed
- **Kardex**: eliminados los fondos de color por tipo de movimiento (verde/rojo/amarillo suaves) que hacían poco legible el texto de los productos — la tabla ahora usa el **mismo estilo de la vista Inventario** (filas alternas estándar)
- Columna y filtro "Tipo" renombrados a **"Documento de:"** (filtro, columna y exportación PDF)

### Verification
- 161 tests passing · EXE recompilado

---

## [2.8.20] — 2026-09-17 — Migración de Materia Prima (bandas de reencauche) + unidad ROLLO

### Added (datos — migración desde Excel)
- **74 bandas de reencauche migradas** desde `DELCA INVENTARIO. MIGRAR.xlsx` (hoja "Materia prima") con `scripts/migrar_materia_prima.py` (dry-run + backup `delca_pre_migrar_mp_20260917_153937.db`):
  - Nombre → `nombre` · Codigo → `sku` (sin código → **generado del nombre**, ej. `BANDAVU165`) · Precio Unitario → `costo_unitario` · KG → `stock_kg` · Rollos → `stock` · Mínimo → `stock_minimo` · Unidad → `ROLLO`
  - **42 movimientos ENTRADA** (kardex) con la fecha de ingreso del Excel (2026-09-14) para bandas con stock
  - Excluida la fila vacía "Banda PBA" · UPSERT por SKU (robusto a re-ejecuciones)
- **Verificación fila a fila: 74/74 coinciden (0 errores)**

### Changed (código)
- **Unidad de medida "ROLLO"**: agregada al CheckConstraint del modelo `productos` y a la lista del formulario de Materia Prima
- **Formulario "Nuevo Producto – Materia Prima"**: campo "Precio Unit. $" renombrado a **"Costo Unitario $"** (define claramente que es el costo de la banda, no su precio de venta)

### Verification
- 161 tests passing · EXE recompilado

---

## [2.8.19] — 2026-09-17 — Unificación de dimensiones + filtros en reporte + stock KG + auto-precio en llanta

### Changed (datos — indicación del negocio)
- **Unificación de dimensiones** (`scripts/unificar_dimensiones.py`, backup `delca_pre_unif_dim_20260917_145115.db`):
  - `95R17.5` → `9.5R17.5` (0 llantas; 6 refs duplicadas del catálogo eliminadas — 9.5R17.5 conserva sus precios)
  - `7R15` → `700R15` (232 llantas; 1 ref duplicada eliminada — 700R15 conserva su precio; 8 refs sin equivalente **movidas con sus precios**)
  - `7R16` → `700R16` (**creada**, 654 llantas; 8 refs movidas con sus precios)
  - Las 3 dimensiones viejas eliminadas (verificado: 0 referencias restantes)

### Added / Changed (código)
- **Reporte de Llantas**: nuevos filtros **Diseño** y **Dimensión** (2 combos, sin botones nuevos) — `reporte_llantas(diseno_id, dimension_id)` + vista
- **Inventario → Nuevo Producto**: "Cantidad inicial" renombrada a "**Cantidad en planta Und**" + nueva casilla "**Cantidad en planta en KG**" (columna `stock_kg` en `productos`, backup `delca_pre_stock_kg.db`)
- **Registro de Llanta**: auto-precio del catálogo con regla completa (normal → mínimo → 1 sin cobertura) — consistente con reporte/facturación

### Verification
- Filtros: dimension_id=28 → 232 llantas · +diseño VT50L → 118
- Producto: stock=10 + stock_kg=250.5 guardado/leído correcto
- Cobertura: 700R15 y 700R16 con 0 llantas sin precio · 161 tests · EXE recompilado

---

## [2.8.18] — 2026-09-16 — Facturación: precio de la llanta pre-rellenado desde el catálogo (automático)

### Changed
- **Diálogo de facturación**: al agregar una llanta, el precio se pre-rellena **desde el catálogo** `precios_producto` (por diseño + dimensión: `precio_normal` → `precio_minimo` → 1 peso sin cobertura) en lugar del dato guardado en la llanta. **Automático, sin botones** — reutiliza el helper `costo_precio`
- El precio sigue siendo **editable** en el diálogo (precios especiales) y el histórico de facturas creadas no cambia
- Archivo: `src/modules/finanzas/views/facturacion_view/_factura_form_dialog.py` (1 punto de cambio, línea del precio)

### Verification
- 24,304 llantas con cobertura → precio del catálogo pre-rellenado (validado vs precios_producto) · 146 sin cobertura → 1 editable
- 161 tests passing · EXE recompilado

---

## [2.8.17] — 2026-09-16 — Reporte de llantas: costo/precio desde el catálogo de Facturación-Precios

### Changed (regla de negocio indicada por el cliente)
- **Costo** (columna Costo del reporte de llantas) = `precios_producto.costo_fabricacion` por **(diseño + dimensión)** — refleja en vivo los ajustes del catálogo
- **Precio** (columna Precio) = **precio de venta** (`precio_normal`) por diseño + dimensión; si la referencia no tiene precio normal → **precio mínimo** (`precio_minimo`)
- **Sin cobertura** en el catálogo → **precio de referencia = 1 peso** (146 llantas; se ajustó también el dato `precio_venta` con backup `delca_pre_precio_sin_cob_20260916_174907.db`)
- Utilidad, margen y KPIs derivados usan estos valores en **toda la herramienta**

### Implementación (nuevo helper `src/modules/llantas/services/costo_precio.py`)
- `reporte_llantas` (filas + KPIs: valor_inventario, utilidad_potencial, con/sin precio)
- `detalle_financiero_llantas` (llantas; las "Llantas nuevas" facturadas conservan su precio real)
- `indicadores_llantas` (resumen + detalle + por_estado con costos del catálogo)
- `inventario_kpi_service` (`resumen_kpis`, `terminadas_en_planta`, `reporte_semanal`)

### Verificación
- 24,304 llantas con cobertura (costo/precio del catálogo validados vs precios_producto) · 146 sin cobertura → precio 1
- 161 tests passing · EXE recompilado

---

## [2.8.16] — 2026-09-15 — Clientes: 15 llantas sin cliente asignadas (migración 100% completa)

### Added
- **15 llantas sin cliente asignadas** por indicación del negocio:
  - **DELCA** (id 4895): 6659, 8251, 9588-90, 12491-92, 12516-17 (9 llantas)
  - **PORTILLO WILBER** (creado: NIT 1085250619, tel 3112563822): 25064-65 (2 llantas)
  - **HERRERA ESTEBAN 2** (creado: NIT 1085106383, tel 3206669663): 25042-45 (4 llantas)
- Script `scripts/aplicar_clientes_15.py` (idempotente, dry-run + backup `delca_pre_llantas_cliente_20260915_110621.db`)

### Resultado
- **0 llantas sin cliente** · 24,450 llantas · 5,241 clientes · **migración 100% completa**

---

## [2.8.15] — 2026-09-15 — Clientes: 18 llantas validadas manualmente + NITs reales corregidos

### Added
- **18 asignaciones de cliente validadas manualmente por el negocio** (llantas con NIT vacío en el legacy): ROSELLANTAS LTDA (1355, 1356), ROBERTO LOPEZ (6142, 13422), GIRALDO RIVERA (7206-08), PEREZ ABELINO (12021-22), GERARDO BRAVO (13351, 19826-27, 23486-87), TORO JOSE DOMINGO (14132, 14540, 15113, 17917). Script `scripts/aplicar_clientes_validados.py` (dry-run + backup `delca_pre_clientes_validados_20260915_102656.db`)

### Fixed
- **NITs reales corregidos** (los anteriores eran derivados del código legacy): ROSELLANTAS LTDA 07213518 → **901585099** · GIRALDO RIVERA 0301 → **005824600** · PEREZ ABELINO 0135 → **0025865400** · GERARDO BRAVO 060 → **0025845600**

### Pending
- **15 llantas sin cliente**: 7 con códigos huérfanos (C4872/C4873) + 8 sin código en MAE_PROD — lista entregada al negocio para validación (`completar_clientes_15_2026-09-15.csv`)

---

## [2.8.14] — 2026-09-14 — Corrección de migración: tiquetes realineados al tiquete físico (TIQUETE2)

### Fixed
- **Tiquetes incorrectos en las 24,450 llantas**: la migración guardó el campo `TIQUETE` del MAE_PROD (secuencia interna con prefijo J, ej. 'J1353') en vez del `TIQUETE2` — el tiquete REAL impreso en la llanta física (ej. '1355'). Verificado en el origen: O.S. 577-1 = tiquete 1355
- **Corrección**: `scripts/corregir_tiquetes.py` — mapeo `llanta.tiquete → TIQUETE2` del MAE_PROD (guardado sin J). TIQUETE2 es único (0 duplicados). Backup: `backups/delca_pre_tiquetes_20260914_185512.db`
- **Post-verificación**: 24,451 tiquetes únicos · 0 duplicados · orden/dimensión/marca **0 discrepancias** vs MAE_PROD (24,450 comparadas) · el reporte funciona (1355 → orden 577-1)

### Pending
- ~~Excepción `J23489`~~ → **RESUELTA**: era una llanta **duplicada** (O.S. 10418-1, BLAK 295/80R22.5) — la misma llanta ya existía con tiquete correcto `24922`. Eliminada con sus historiales por orden del negocio (backup `delca_pre_eliminar_duplicada_20260915_093917.db`). **Total: 24,450 llantas · 0 tiquetes duplicados · 0 con prefijo J**

### Docs
- `docs/MIGRACIONES.md`: regla 1c — verificar el identificador contra el valor **impreso** en el artículo físico (campo TIQUETE vs TIQUETE2)

---

## [2.8.13] — 2026-09-14 — Clientes: decisión de NO unificar por NIT · 18 asignaciones NO aplicadas (revertidas)

### Changed (decisión del negocio)
- **NO se unifican clientes por coincidencia de NIT ni nombre**: los 11 grupos (318 llantas) donde el nombre legacy existe en DELCA con NIT distinto se dejan como quedaron post-corrección por NIT. Motivo: la coincidencia de NIT no garantiza la misma persona/empresa (caso RIVERA MANUEL vs RIVERA FAJARDO: conteo por NIT 6, verificación manual 7)
- **18 asignaciones por nombre REVERTIDAS**: se aplicaron temporalmente (ROSELLANTAS, ROBERTO LOPEZ, GIRALDO RIVERA, PEREZ ABELINO, GERARDO BRAVO, TORO JOSE DOMINGO) y se revirtieron por decisión del negocio. Las 18 llantas quedan en el cliente asignado por NIT (estado pre-aplicación restaurado desde `backups/delca_pre_asignaciones18_20260914_173230.db`)
- **Órdenes**: sin cambios (las 143 órdenes con >1 cliente son fieles al MAE_PROD — no se modificaron)

### Pending (validación del negocio)
- 18 llantas con NIT vacío en legacy y nombre distinto (sin asignar por nombre)
- 15 llantas sin cliente: 7 con códigos huérfanos (C4872/C4873 — no existen en MAE_CLIENTE) + 8 sin código en MAE_PROD

### Docs
- `docs/MIGRACIONES.md`: nueva regla 1b — no unificar por coincidencia de NIT; confiar en la verificación manual cuando un conteo no cuadre

---

## [2.8.12] — 2026-09-14 — Corrección de migración: clientes de llantas realineados por NIT (4,196 llantas)

### Fixed
- **Cliente incorrecto en 4,196 llantas (17%)**: la migración original insertó los clientes sin id (ids secuenciales de SQLite) y las llantas copiaron el `COD_CLIEN` del legacy convertido a número con corrimientos por bloque → llantas apuntando a clientes existentes pero equivocados. Verificado contra el **MAE_PROD.DBF original** (no solo el CSV): 3,911 discrepancias por nombre, 4,196 por NIT
- **Corrección**: `scripts/corregir_clientes_nit.py` — mapeo `llanta.tiquete → MAE_PROD.COD_CLIEN → MAE_CLIENTE.NIT_CLIEN → cliente.id` (llave natural NIT, **0 ambigüedades**: 5,239 NITs únicos en DELCA, todos los NITs legacy existen). Backup: `backups/delca_pre_clientes_20260914_163911.db`
- **Post-verificación**: 24,051 llantas con cliente verificado por NIT · **0 errores reales restantes** (318 casos son el mismo cliente con distinta denominación entre sistemas, ej. `CH-Z Y CIA SCS` = `CHAVEZ ZARAMA FERNANDO`, mismo NIT)

### Pending (requieren validación del negocio — NO corregibles mecánicamente)
- 18 llantas con NIT vacío en MAE_CLIENTE y nombre legacy distinto (ej. J6106 `ROBERTO LOPEZ` vs `BASTIDAS SILVIO`)
- 15 llantas sin cliente: 7 con códigos huérfanos (C4872/C4873 no existen en MAE_CLIENTE) + 8 sin código en MAE_PROD
- Detalle: `correccion_clientes_EXCEPCIONES_2026-09-14.csv`, `verificacion_clientes_POST_2026-09-14.csv`

### Docs
- **`docs/MIGRACIONES.md`**: lecciones aprendidas para futuras migraciones — nunca usar ids autoincrementales del destino, migrar por llave natural (NIT), verificar siempre contra el DBF origen, chequear referencias huérfanas, patrón dry-run + backup

---

## [2.8.11] — 2026-09-14 — Corrección de migración: costos alineados al catálogo + reporte de incongruencias de clientes

### Fixed
- **Costo de fabricación vacío en el reporte de Llantas**: 8,052 llantas (33%) no tenían `costo_produccion`, aunque el costo existía en `precios_producto.costo_fabricacion` (catálogo de Facturación-Precios). Nuevo script `scripts/corregir_costos_produccion.py` alinea TODAS las llantas al costo del catálogo por diseño+dimensión (con backup y dry-run): **24,305/24,451 llantas con costo** (antes 16,399) — el reporte de Llantas ya muestra el costo
- **Nota**: el costo histórico del DBF no coincidía con el catálogo en ninguna llanta (24,305 cambiaron); se adoptó el catálogo como fuente de verdad (confirmado por el usuario)

### Added
- **Reporte de incongruencias de clientes**: `incongruencias_clientes_2026-09-14.csv` (carpeta DELCA) — **547 llantas en 143 órdenes con >1 cliente distinto** (el `cliente_id` migrado del ETL legacy es incorrecto en esas filas; la info técnica es correcta). El reporte permite la validación del negocio antes de corregir (NO se corrigieron clientes sin validación)

### Verification
- **BD**: 24,305/24,451 con costo (146 sin costo = combinaciones sin precio en catálogo)
- **Reporte de Llantas**: costo visible en las filas
- **Suite de tests**: 161 passed
- **EXE recompilado** (exit 0)

---

## [2.8.10] — 2026-09-03 — Clientes inactivos: excluye actividad reciente (últimos 10 meses)

### Changed
- **Nueva condición en la lógica de Activo/Inactivo (todo el sistema)**: un cliente con actividad en los **últimos 10 meses** NUNCA se lista como inactivo, sin importar el segmento seleccionado — no se llama a recuperar a quien trajo llantas recientemente
- **Definición final**:
  - **ACTIVO** = llantas en planta/producción **o** actividad posterior al fin del segmento **o** actividad en los últimos 10 meses
  - **INACTIVO** = sin llantas + última actividad ≤ hasta + sin actividad en los últimos 10 meses + con historial previo
- Corrige: CHAPAL MARCOS (última actividad 24/06/2026) y CHALACAN WILLIAM (09/05/2026) ya NO aparecen en el reporte de inactivos de ningún segmento

### Verification
- **CHALACAN WILLIAM / CHAPAL MARCOS**: excluidos en los 3 segmentos probados ✓
- **Último año**: 458 inactivos (antes 519) — 0 con actividad posterior a hace 10 meses
- **Dashboard/Resumen/Por Ciudad coherentes**: 1,101 activos / 4,138 inactivos
- **Suite de tests**: 151 passed
- **EXE recompilado** (16:28)

---

## [2.8.9] — 2026-09-03 — Clientes Activo/Inactivo: lógica B aplicada en todo el sistema

### Changed
- **Definición confirmada (opción B) aplicada en TODO el sistema** (reporte Activos/Inactivos, Dashboard, Resumen, Clientes Por Ciudad):
  - **ACTIVO** = tiene ≥1 llanta en planta/producción **o** tuvo actividad **DESPUÉS del fin del segmento** (última actividad > hasta — el cliente siguió trayendo)
  - **INACTIVO** = sin llantas en planta/producción **y** última actividad ≤ hasta (dejó de venir a más tardar al final del periodo) **y** con historial previo (alguna vez trajo llantas)
- **Corrige el error reportado**: clientes con actividad posterior al segmento (ej. ARCOS FREDY MARLON, último movimiento 31/03/2026) ya NO aparecen como inactivos — están activos y no deben llamarse para recuperar
- El segmento [desde, hasta] define el periodo: **el fin del segmento es el umbral** de la última actividad

### Verification
- **Segmento [03/09/2023, 03/09/2024]**: 325 inactivos — ARCOS FREDY MARLON y ARGOTI ALEXANDER EXCLUIDOS ✓
- **Dashboard/Resumen/Por Ciudad coherentes**: 1,040 activos / 4,199 inactivos (con hasta = hoy, activos = llantas en planta)
- **Suite de tests**: 151 passed
- **EXE recompilado** (11:51)

---

## [2.8.8] — 2026-09-03 — Reportes: selectores de fecha robustos + protección de refrescos

### Fixed
- **Selectores "Desde"/"Hasta" verificados**: en código aceptan cambio de fecha y refrescan el reporte correctamente (verificado: cambio programático + flujo completo filtro Inactivo + segmento 2024 → 402 filas). El último ajuste (clasificación de inactivos) no tocó la UI de fechas — si el cambio no se reflejaba, era la app abierta con una versión anterior
- **Refrescos protegidos con try/except** (Clientes ×3, Finanzas ×3): si el service lanza un error con ciertas fechas, la vista muestra "(Error al generar el reporte: ...)" en la tabla en vez de abortar el proceso (PySide6 ≥6.5 aborta las excepciones de slots) o dejar la UI bloqueada

### Verification
- **Vista + refrescos con protección**: construyen y cargan sin error
- **Suite de tests**: 151 passed (26.8 s)
- **EXE recompilado** (11:15)

---

## [2.8.7] — 2026-09-03 — Reporte inactivos: solo clientes que cumplieron inactividad en el segmento

### Fixed
- **El filtro "Inactivo" incluía a todos los inactivos totales** (incluyendo clientes sin NINGÚN historial — nunca trajeron llantas). Ahora **solo muestra los clientes que cumplen inactividad en el segmento seleccionado**: con historial previo (alguna vez fueron clientes activos de DELCA) y sin movimientos dentro de [desde, hasta] ni llantas en planta/producción
- **Los clientes sin historial se excluyen** (3,680 de 5,239): nunca trajeron llantas, no son recuperables — llamarlos no tiene sentido

### Verification
- **Segmento 03/09/25 → 02/09/26**: INACTIVOS = **435** (antes 4,117) — todos con historial previo (0 sin historial)
- **Suite de tests**: 151 passed
- **EXE recompilado** (10:58)

---

## [2.8.6] — 2026-09-03 — Activos/Inactivos: el segmento de fechas define el periodo de inactividad

### Changed
- **El filtro de fechas [desde, hasta] define el SEGMENTO donde se evalúa la inactividad**: un cliente es **INACTIVO en ese segmento** si **no tuvo NINGÚN movimiento dentro de él** (ingresos de llantas, cambios de estado, entregas/ubicaciones, facturas) **y** no tiene llantas en planta/producción. Antes solo usaba "desde" como umbral del último movimiento; ahora el rango completo delimita la actividad evaluada
- **Uso para recuperación de clientes**: al seleccionar "Inactivo" + un periodo (ej. 2024, el último año, o cualquier rango), el reporte carga los clientes sin movimientos en ese tramo — el usuario estructura las llamadas por periodos y arma el plan de recuperación. La columna "Última Vez" muestra su última actividad real para priorizar
- Dashboard/Resumen usan el rango por defecto (último año) → **coherentes** con el reporte

### Verification
- **Default (último año)**: 1,122 activos / 4,117 inactivos — dashboard y reporte idénticos
- **Segmento 2024**: 4,082 inactivos (clientes sin movimientos en 2024) · **Últimos 3 meses**: 1,051 activos
- **Suite de tests**: 151 passed
- **EXE recompilado** (10:46)

---

## [2.8.5] — 2026-09-02 — Reportes: fix Mayor Saldo + mensajes claros en tablas vacías

### Fixed
- **Mayor Saldo salía vacío**: el reporte filtraba/ordenaba por el campo legacy `Cliente.saldo` y las fechas se aplicaban sobre un `outerjoin` con facturas → con 0 facturas o fechas fuera de rango eliminaba todo. Ahora el saldo se calcula de las **facturas reales** (suma por cliente, `estado != ANULADA`, `saldo > 0`) y las fechas filtran DENTRO del subquery — robusto con cualquier periodo
- **Mensajes claros en reportes vacíos** (antes "(sin datos)" genérico): Finanzas por Mes/Estado → **"No hay facturas en el periodo seleccionado"**; Mayor Saldo → **"No hay clientes con saldo pendiente"**

### Contexto
- **La BD tiene 0 facturas** (la limpieza v2.7.2 eliminó las legacy y no hay facturación nueva desde la app) → los reportes de Finanzas por Mes/Estado están vacíos por falta de datos, no por fallo de la vista. Al facturar desde la app se llenarán solos

### Verification
- **Prueba interna de 14 tablas**: 11 con datos correctos (Clientes 5,239 · Llantas 741 · Detalles · Inventario · Resumen) y 3 vacías con mensaje claro (por falta de facturas)
- **Suite de tests**: 151 passed (25.6 s)
- **EXE recompilado** (exit 0)

---

## [2.8.4] — 2026-09-02 — Reportes: botón "Visualizar" + conteo visible en la barra

### Added
- **Botón "👁️ Visualizar" en las 6 secciones con exportar** (Clientes Activos/Inactivos y Mayor Saldo, Finanzas por Mes/Estado/Detalle Llantas, Llantas): carga la tabla con los filtros actuales para verificar la información ANTES de exportar a Excel (1:1 con cada botón "📊 Exportar Excel")
- **Barra de resumen con el conteo del reporte** (visible sin exportar): los reportes de Clientes ahora dicen **"Clientes en el reporte: X"** (antes "Total clientes"); Finanzas muestra "Facturas: X"; Llantas e Inventario ya mostraban su total

### Verification
- **6 botones Visualizar** verificados (1:1 con los 6 Exportar) — vista construye OK
- **Barra de resumen** con conteo visible en todas las secciones (ej. "Clientes en el reporte: 5,239")
- **Suite de tests**: 151 passed
- **EXE recompilado** (exit 0)

---

## [2.8.3] — 2026-09-02 — Clientes activos: definición UNIFICADA en toda la app

### Fixed
- **Inconsistencia: Dashboard mostraba "314 / 5,239" clientes activos vs Reporte "1,124"**: la definición de "cliente activo" estaba implementada en 3 variantes incompatibles:
  - Dashboard (314): solo llantas en planta con `fecha_ingreso` en el último año (incompleta — no contaba entregas, estados, facturas ni clientes sin llantas en planta)
  - Resumen de reportes (5,239): campo legacy `Cliente.activo` (marcado 1 para todos)
  - Reporte de clientes (1,124): actividad completa (correcta)
- **Solución**: nuevo módulo central `src/core/services/cliente_actividad.py` (único punto de verdad) con la definición confirmada (llantas en planta/producción **o** cualquier movimiento en el periodo). Las 3 secciones lo usan → **coherentes en 1,124 activos / 4,115 inactivos**
- **Filtros legacy eliminados**: cartera (Finanzas) y combo de clientes de facturación ya no filtran por `Cliente.activo` (campo sin significado real) — la facturación permite seleccionar cualquier cliente

### Verification
- **Coherencia verificada**: Dashboard "1,124 / 5,239" = Resumen reportes (1,124/4,115) = Reporte Activos/Inactivos (1,124/4,115) ✓
- **Suite de tests**: 151 passed (26.3 s)
- **EXE recompilado** (exit 0)

---

## [2.8.2] — 2026-09-02 — Estado Activo/Inactivo de clientes: actividad COMPLETA + coherencia entre pestañas

### Fixed
- **Clientes activos marcados inactivos (revisión)**: la definición ahora se basa en **TODAS las fechas de actividad en la BD** (unión de ingresos de llantas + cambios de estado + cambios de ubicación/entregas + facturación), no solo el último ingreso. Un cliente es **ACTIVO** si tiene ≥1 llanta en planta/producción **o** tuvo cualquier movimiento en el periodo; **INACTIVO** si no tiene llantas en planta/producción **y** ≥1 año sin movimientos
- **Inconsistencia entre pestañas corregida**: la pestaña "Clientes → Por Ciudad" mostraba el estado con el campo legacy `Cliente.activo` (marcaba TODOS como "Activo") mientras "Activos/Inactivos" usaba la definición dinámica — un cliente aparecía "Activo" en una y "Inactivo" en otra. Ahora ambas usan la misma definición dinámica (coherentes)
- **"Última Vez"** muestra la última actividad completa (movimiento más reciente en la BD)

### Verification
- **Conteos coherentes**: Activos 1,124 · Inactivos 4,115 · Total 5,239 — IDENTICOS en ambas pestañas (verificado)
- **Diagnóstico**: de los 4,115 inactivos, 0 tenían actividad alternativa reciente (la definición por ingresos era consistente; la ampliación a actividad completa la hace robusta)
- **Suite de tests**: 151 passed (27.2 s)
- **EXE recompilado** (exit 0)

---

## [2.8.1] — 2026-09-02 — Reportes: carga rápida + clientes activos/inactivos con definición correcta

### Fixed
- **"Clientes inactivos" salía vacío**: el reporte filtraba con el campo legacy `Cliente.activo` (marcado 1 para todos los 5,239 clientes migrados → 0 inactivos) y las fechas no filtraban nada. Ahora usa la **definición operativa confirmada**:
  - **ACTIVO** = tiene ≥1 llanta en planta/producción (no entregada) **o** ingresó llantas dentro del periodo seleccionado
  - **INACTIVO** = sin llantas en planta/producción **y** ≥1 año sin movimientos en la BD (último ingreso anterior al inicio del periodo)
  - Resultado actual: **4,115 inactivos + 1,124 activos** = 5,239 ✓
  - El reporte ahora muestra el **último ingreso de llanta** ("Última Vez") en vez de la última factura
- **Carga lenta del módulo Reportes**: ahora **carga diferida (lazy)** — al abrir solo carga la pestaña visible (Clientes, ~1.8 s); las demás pestañas cargan al seleccionarse por primera vez y quedan en caché. Antes ejecutaba ~13 queries pesadas al abrir
- **Índices de base de datos** (migración v2.8.1, una sola vez): `ix_llantas_estado`, `ix_llantas_ubicacion_actual`, `ix_facturas_fecha_emision` — aceleran las queries de reportes/dashboard sobre 24,451 llantas

### Verification
- **Reporte**: inactivos 4,115 / activos 1,124 (0.18 s por query — con índices)
- **Carga del módulo**: 1.83 s al abrir (antes: decenas de segundos); pestañas perezosas + caché
- **Suite de tests**: 151 passed (27.0 s)
- **EXE recompilado** (exit 0)

---

## [2.8.0] — 2026-09-02 — INSPECCION INICIAL: botón renombrado + fix búsqueda por tiquete

### Changed
- **Botón "⚡ Cambio Rápido" → "⚡ INSPECCION INICIAL"** (módulo Llantas) — nombre según documentos de certificación
- **Título del diálogo** → "INSPECCION INICIAL" (coherencia)

### Fixed
- **"Llanta no encontrada" en la casilla tiquete**: el diálogo buscaba el tiquete con coincidencia EXACTA contra la BD (que guarda el prefijo "J"), pero el usuario escribe el número sin la "J" (como se muestra en las tablas desde v2.7.6). Búsqueda normalizada: acepta `24537` y `J24537` (mismo patrón que Producción/Planta)
- Verificado con tiquete real APTA: encontrado con y sin "J"

### Verification
- **Suite de tests**: 151 passed (30.7 s)
- **EXE recompilado** (3:43 PM) con el comando estándar restaurado

---

## [2.7.9] — 2026-09-02 — Reparación de launchers del venv (pyinstaller.exe, pytest.exe)

### Fixed
- **`pyinstaller.exe` y `pytest.exe` del venv no ejecutaban** (exit 1 silencioso): los launchers `.exe` de Scripts de la instalación original (24/06/2026) se habían corrompido — 14/14 fallaban (pyinstaller, pytest, coverage, fonttools, pyi-*, etc.), mientras `pip.exe` (reinstalado el 24/07) y los módulos (`python -m PyInstaller`) funcionaban. Causa probable: corrupción de los binarios por la sincronización de OneDrive sobre la carpeta del proyecto
- **Solución**: reinstalación forzada de los paquetes (`pip install --force-reinstall --no-deps`): PyInstaller 6.22.2, pytest 9.1.1, coverage 7.16.0, fonttools 4.64.0, Pygments 2.21.0, python-dotenv 1.2.3 → los launchers se regeneraron sanos
- **Verificado**: `pyinstaller.exe build_exe.spec --clean -y` funciona (EXE recompilado con el comando estándar), `pytest.exe` ejecuta, EXE arranca (vivo a los 20 s)
- **Nota**: `python -m pytest` sigue siendo la vía recomendada para los tests (el launcher no añade el CWD al sys.path)

---

## [2.7.8] — 2026-09-02 — Dashboard: cards con estados y ubicación específicos

### Changed
- **Card superior "Llantas en Planta" → "Reencauchada en Planta"**: ahora cuenta SOLO llantas `REENCAUCHADA` físicamente en `PLANTA` (780). Antes sumaba todos los estados no entregados (6,465, incluyendo producción)
- **Card superior "En Producción" → "Aptas+Pendiente"**: ahora cuenta `APTA` + `PENDIENTE` físicamente en `PLANTA` (631 + 308 = 939)
- **Sección "Llantas por Estado"**: se mantienen las 3 cards existentes (En Proceso 4,620 · En Planta 6,465 · Rechazadas) y se **agrega "Reparaciones"** (126, estado `REPARADA` en `PLANTA`)
- Los valores son dinámicos (consultan la BD en cada carga) — dependen de la operación y producción de la empresa

### Verification
- **Métricas verificadas**: Reencauchada en Planta 780 ✓ · Aptas+Pendiente 939 ✓ · Reparaciones 126 ✓ (sin cambios en las cards de estado existentes)
- **Suite de tests**: 151 passed (34.6 s)
- **EXE recompilado** (71.6 MB) y arrancando (vivo a los 22 s)
- **Nota**: el `pyinstaller.exe` del venv quedó dañado (falla con exit 1 sin salida) — se compila con `python -m PyInstaller`

---

## [2.7.7] — 2026-09-01 — N° de Orden con consecutivo (1-12)

### Changed
- **El N° de Orden (O.S.) se muestra con su consecutivo** (`64230C-1`): una orden agrupa hasta 12 tiquetes y cada uno lleva su casilla/consecutivo. El campo `consecutivo` estaba en la BD (24,451/24,451 migrados) pero nunca se mostraba
- **Nuevo helper central** `formatear_orden(numero_orden, consecutivo)` en `llanta_service/_core.py` (presentación pura, no modifica la BD)
- **Aplicado en**: impresión de la hoja de proceso (campo O.S.), tablas de Llantas, Producción, Planta y dict de Inventario

### Verification
- **Helper probado**: `formatear_orden('64230C','1')`→`'64230C-1'`, `'5615','12'`→`'5615-12'`, sin consecutivo→solo la orden
- **Ejemplo real**: tiquete J3 → orden "2-3" (orden 2, consecutivo 3)
- **Suite de tests**: 151 passed (32.9 s)
- **EXE recompilado** (71.6 MB) y arrancando (vivo a los 25 s, sin WER nuevos)

---

## [2.7.6] — 2026-08-31 — Tiquete sin prefijo "J" en toda la app

### Changed
- **Tiquetes visibles SIN el prefijo "J" de la serie en toda la aplicación**: el campo `tiquete` almacena el identificador completo (ej. "J24537", prefijo fijo en los 24,451 registros); ahora TODAS las vistas lo muestran solo con el número ("24537")
- **Nuevo helper central** `formatear_tiquete()` en `llanta_service/_core.py` (presentación pura — NO modifica la BD)
- **Aplicado en**: tablas de Llantas, Producción, Planta, Inventario (llantas terminadas), Reportes (3 vistas), y facturación (combo, tabla de ítems y labels)
- **Búsquedas por tiquete normalizadas** (Producción y Planta): aceptan "24537" o "J24537" — si el texto no lleva el prefijo, se busca con "J" (la BD lo guarda con prefijo)

### Verification
- **Imports verificados**: todos los módulos modificados importan correctamente
- **`formatear_tiquete` probado**: "J24537"→"24537", "24537"→"24537", None→""
- **Suite de tests**: 151 passed (27.1 s)
- **EXE recompilado** (66.3 MB)

---

## [2.7.5] — 2026-08-31 — Impresión de la Hoja de Proceso (formato aprobado)

### Fixed
- **Impresión del tiquete salía en BLANCO**: `tiquete_printer.py` usaba `doc.drawContents()` con `setPageSize` en puntos (1/72") sobre un `QPainter` de 1200 dpi → el contenido se comprimía en ~4.4×6.3 mm (invisible). Además, `setPageOrientation(Landscape)` con tamaño explícito intercambiaba el MediaBox del PDF (distorsión al renderizar). Corregido: se eliminó el HTML genérico y el renderizado manual

### Changed
- **Impresión por overlay sobre el formato aprobado**: la "Hoja de Proceso de Reencauche" escaneada (formato inmodificable, aprobado por acreditación, 1152×423 mm) se imprime como FONDO y los datos de la llanta se superponen en los espacios en blanco
- **Fondo pre-renderizado**: `assets/hoja_proceso_reencauche.png` (150 dpi) — evita dependencia de QtPdf en runtime; empaquetado en el EXE (`build_exe.spec` incluye assets/)
- **Campos superpuestos (texto horizontal, como el llenado manual)**: Cliente, N° Tiquete, Dimensión, Diseño, O.S. (número de orden) y Serie (= DOT, según confirmación del usuario) — en los DOS bloques del formato (talón y cuerpo)
- **N° Tiquete sin prefijo "J"**: los 24,451 tiquetes de la serie llevan el prefijo fijo "J" (J24537); al imprimir se elimina (`removeprefix("J")`) → solo el número (24537)
- **`build_exe.spec`**: añadidos `assets/hoja_proceso_reencauche.png` y `assets/delca.ico`

### Verification
- **Overlay verificado objetivamente** (diferencia de píxeles fondo vs fondo+datos): texto presente en 11/11 celdas del panel izquierdo (27-44% de píxeles cambiados por celda), 0.0% en zonas de control (nada fuera de lugar)
- **MediaBox corregido** (3266×1199 pt landscape, sin distorsión)
- **Suite de tests**: 151 passed
- **EXE recompilado** (66.3 MB, incluye el fondo del formato)

---

## [2.7.4] — 2026-08-29 — Fix crash al maximizar + ventana maximizada

### Fixed
- **Crash nativo al maximizar la ventana (0xC0000005 en Qt6Widgets.dll `0x3e1543`)**: `DashboardView._delete_old_chart()` eliminaba el **chart interno por defecto del QChartView** (existe incluso sin `setChart`) vía `deleteLater()`. Con la BD sin facturas (0 resultados tras la limpieza v2.7.2), `_render_bar_chart` hacía `return` temprano sin setear un chart nuevo → el QChartView quedaba con su scene dañada (item raíz eliminado) → al maximizar, `QGraphicsView` repintaba usando el chart liberado → **use-after-free → access violation** (mismo offset que los crashes WER del usuario: `Qt6Widgets.dll 0x3e1543`)
- **Fix**: `_delete_old_chart()` ahora elimina SOLO el chart creado por el dashboard (tracking con `self._chart_owned`), nunca el default del view. Aplicado también de forma preventiva en `kpi_historico_dialog.py` (mismo patrón)

### Changed
- **La ventana principal abre MAXIMIZADA** (`showMaximized()` tras el login): aprovecha toda la pantalla. Antes abría a 1200×700 (≈78% del ancho en pantallas con DPI 125%), lo que el usuario percibía como "tamaño reducido"

### Verification
- **Repro exacto** (fuente, login real + maximizar): antes crash inmediato (`Fatal Python error: Aborted` / 0xC000041D); después proceso vivo 45 s, exit 0
- **Repro mínimo aislado**: QChartView sin setChart + deleteLater(chart interno) + maximizar → crash confirmado; sin el deleteLater → vivo. Mecanismo 100% aislado
- **Bisección por vistas**: crash solo con DashboardView real; chart aislado no crashea → interacción `_delete_old_chart` + maximize confirmada
- **Navegación completa 14 páginas** (ventana maximizada): sin crash, exit 0
- **Suite de tests**: 151 passed (27.4 s)
- **EXE recompilado y validado** (login real vía UI Automation): ventana abre MAXIMIZADA (1920×991), proceso vivo tras 15 s en la ventana crítica, 0 eventos WER nuevos

---

## [2.7.3] — 2026-08-28 — Fix crash nativo al iniciar (0xC000041D)

### Fixed
- **Crash nativo al abrir la app (0xC000041D / access violation en Qt6Widgets.dll)**: el botón "🧾 Nuevo Producto" de la vista Inventario tenía un **QSS malformado** — `QPushButton { background: ... border: none; }}` con llave de cierre duplicada. Causa: la primera línea del f-string escapaba `{{` → `{` sin cerrar, y la segunda línea (string normal, sin escape) producía `}}` literal → stylesheet desbalanceado. Qt no podía parsearlo y `QStyleSheetStyle` crasheaba al pintar el primer render (~9 s después del login, exactamente el patrón del usuario). Reproducido con main.py real + login real + faulthandler: antes `Windows fatal exception: access violation` (exit -1073740771); después exit 0, 90 s sin crash, 0 warnings Qt
- **Mismo bug latente corregido en 7 botones más** (QSS con `}}` duplicado por concatenación f-string + string normal): `inventario_view/_widgets.py` (3 botones), `precios_view.py` (3 botones) y `inventario_view/_documento_dialogs.py` (1 botón)
- **Propiedades QSS inválidas eliminadas** (`opacity` no existe en Qt Style Sheets → warnings "Unknown property"): `kpi_historico_dialog.py` (hover) y `automatizacion_view/_view.py` (hover/pressed)

### Verification
- **Repro exacto** (main.py real + login real + dashboard, sin navegar): antes 3× "Could not parse stylesheet of object QPushButton" + crash nativo; después 0 warnings, 0 excepciones, proceso vivo 90 s, exit 0
- **Navegación completa por las 14 páginas** del sidebar sin crash (incluye Usuarios, donde el repro anterior crasheaba)
- **Análisis AST de todo el proyecto**: 1,222 concatenaciones de strings revisadas, 0 con llaves desbalanceadas
- **Suite de tests**: 151 passed (32.9 s)
- **EXE recompilado** (`pyinstaller build_exe.spec --clean -y`, `dist/DELCA ERP.exe` 61.3 MB) y validado: arranque OK, proceso vivo a los 25 s, 0 eventos WER nuevos, cierre limpio
- **EXE + login real automatizado** (UI Automation): credenciales `test_repro2`/`Test1234!` en la ventana nativa → login OK (ventana cerrada, MainWindow "DELCA ERP - T2" renderizado), proceso vivo 25 s después del login (ventana crítica: el usuario crasheaba ~9 s tras el login), 0 eventos WER nuevos, `last_login` actualizado en BD

---

## [2.7.2] — 2026-08-28 — Limpieza de facturas de prueba + fix cartera

### Fixed
- **Cartera pendiente excluye facturas ANULADAS**: la query `SUM(saldo)` ahora filtra `estado != 'ANULADA'` (antes incluía la FAC-0003 anulada, sobreestimando la cartera)

### Removed
- **Eliminadas las 13 facturas legacy de prueba** (FAC-0001 a FAC-0013) creadas en desarrollo, junto con sus 11 pagos y vínculos (`factura_llantas`). Estas facturas inflaban la cartera ($4,166,000) y el gráfico de facturación mensual con datos que no corresponden a operación real
- **KPI histórico legacy eliminado** (julio $4,068,000) — el sistema regenera el mes actual al abrir el dashboard
- Nuevo script `scripts/limpiar_facturas_prueba.py` (dry-run/ejecutar con backup)

### Resultado
- **Cartera pendiente: $0** · **Facturación del mes: $0** · **Gráfico mensual: sin barras legacy** — el dashboard refleja la realidad (aún no hay facturación con las llantas migradas)

---

## [2.7.1] — 2026-08-27 — Dashboard: clientes activos reales

### Changed
- **Card "Clientes" del dashboard ahora muestra activos reales / totales** (`316 / 5,239`): la métrica cuenta clientes con ≥1 llanta en planta (no entregada) en el último año, en lugar de usar el campo `activo` del catálogo legacy (que marcaba 1 para todos los migrados). El dato se calcula dinámicamente desde la BD en cada carga del dashboard.

---

## [2.7.0] — 2026-08-27 — Optimización de rendimiento

### Performance
- **Paginación en módulos de llantas**: LlantasView, PlantaView y ProduccionView cargan 500 llantas por página con controles "← Anterior / Siguiente →" y contador. **Apertura de módulos: ~3 s → <100 ms** (38-43x más rápido), memoria 80-130 MB → ~2 MB
- **`listar_llantas()`/`buscar()` paginados**: retornan `(llantas, total)` con `limite`/`offset` en SQL
- **Lazy loading de relaciones**: `lazy="joined"` → `lazy="selectin"` en `llanta_model` (cliente, marca, dimensión, diseño)
- **`reporte_llantas()` optimizado**: KPIs calculados con SQL agregado (`COUNT`/`SUM`/`CASE`) sobre el total; filas detalladas paginables (`limite`/`offset`); la vista limita a 2,000 filas en la tabla manteniendo KPIs del total
- Nuevo test: paginación sin duplicados entre páginas

---

## [2.6.4] — 2026-08-27 — Corrección de fechas de historiales

### Fixed
- **Dashboard "Entregadas del mes" distorsionado**: el importador creaba historiales con fecha de migración (25/08), inflando la métrica a 16,382. Ahora los historiales iniciales usan la `fecha_ingreso` real de cada llanta → la métrica muestra 26 (datos reales de agosto 2026)
- **`importar_llantas_csv.py`**: historiales iniciales usan `fecha_ingreso` (para futuras migraciones)
- **`corregir_historiales_fechas.py`**: script SQL masivo que corrige historiales existentes (24,451 estados + 24,451 ubicaciones) y crea índices faltantes (`ix_estados_llanta_llanta_id`, `ix_ubicaciones_llanta_llanta_id`)

---

## [2.6.3] — 2026-08-27 — Limpieza de código muerto

### Removed
- **22 elementos de código muerto eliminados** (verificación cruzada con vulture + grep fino de referencias):
  - `cliente_service`: `clasificacion_abc`
  - `documento_service`: `crear_documento`, `agregar_movimiento`, `eliminar_documento`
  - `inventario_config_service`: `listar_costos`, `obtener_costo`, `guardar_costo`, `eliminar_costo`, `obtener_precio`, `listar_recetas`, `guardar_receta`, `eliminar_receta`
  - `inventario_kpi_service`: `margen_bruto_operacion`
  - `producto_service`: `obtener_kardex`, `obtener_resumen_stock`, `listar_categorias`
  - `llanta_repository`: `get_by_estado`, `update_cliente`, `get_all_disenos`
  - `catalogos_view/_dialog`: `_parse_rin`
  - `_documento_dialogs`: clase `_LineaProductoDialog`
  - `usuario_service`: `obtener_usuario`
  - `config`: property `is_postgres`
  - `session_service`: import `Optional` sin usar
- Verificación: 150 tests passing, imports de módulos afectados OK, exe recompilado y arrancando

---

## [2.6.2] — 2026-08-25 — Unificación de diseños duplicados

### Added
- **`scripts/unificar_disenos.py`**: detecta y unifica diseños duplicados por normalización de nombre (guiones) — canónico = nombre sin guion, duplicado = con guion

### Changed
- **Unificados 3 duplicados** (1,672 llantas reasignadas): `DV-RT4 → DVRT4` (1,514), `DV-RT2 → DVRT2` (145), `PBT14-W → PBT14W` (13)
- Tras la unificación, **1,287 precios adicionales aplicados** (DVRT4 295/80R22.5 = 960,000 confirmado) — total 9,002 llantas con precio
- **`formato precios a cargar.xlsx` actualizado**: 4 hojas (Precios top 25, Pendientes 359 combinaciones/9,894 llantas, Ya con precio 97, Instrucciones)

---

## [2.6.1] — 2026-08-25 — Precios aplicados a llantas terminadas

### Added
- **`scripts/aplicar_precios.py`**: copia `precio_normal` de `precios_producto` → `llantas.precio_venta` para llantas REENCAUCHADA/REPARADA con cobertura (dry-run/ejecutar con backup; solo pisa precios vacíos)
- **`PrecioProductoService.aplicar_precios(llanta_id=None)`**: método reutilizable e idempotente (desde UI o script)
- Reportes: `precios faltantes.csv` (por llanta), `combinaciones sin precio.csv` + `docs/reporte_precios_sin_cobertura.txt` (362 combinaciones, 11,181 llantas sin cobertura)
- Tests de `aplicar_precios()` (4 nuevos: copia, sin cobertura, no pisa existente, idempotente)

### Changed
- **7,712 llantas recibieron precio** (`precio_normal`); 11,181 quedan sin precio (sin cobertura en `precios_producto` — pendiente cargar desde Excel de precios)
- Suite de tests: 150 passing

---

## [2.6.0] — 2026-08-25 — Dimensiones: ancho FLOAT + sufijo visible

### Added
- **Dimensión de llanta ampliada**: `ancho` pasa de INTEGER a FLOAT (soporta `9.5`, `7.50`, `8.25`) y nueva columna `sufijo` (visible: `215/75R16C`, `295/80R22.5U`); UNIQUE ahora incluye el sufijo
- **Parser ampliado** (`parsear_dimension`): ancho decimal, sufijos de letra, métrico con guion (`215/75-15`), rin decimal en convencional (`12-22.5`), flotación (`31X10.50R15`), especial sin ancho (`H78-15`)
- **Script `resolver_dimensiones.py`**: re-vincula las llantas con `dimension_id IS NULL` (dry-run/ejecutar con backup)
- Migración BD v2.6.0 + tests (14 nuevos: parser y servicio de dimensión)

### Changed
- **1,637 llantas vinculadas** a catálogo (0 pendientes); 13 dimensiones nuevas creadas (9.5R17.5, 7.5R16, 215/75R16C, etc.)

---

## [2.5.0] — 2026-08-24 — Modelo "flujo correcto 2"

### Added (Nuevas Funcionalidades)

#### Modelo de estados y ubicaciones
- Nuevo estado `REPROCESO` (6 estados totales) según "flujo correcto 2"
- Matriz de transiciones centralizada en `_constantes.py` (`TRANSICIONES_VALIDAS`)
- `VEREDICTO_UBICACION` centralizado (APTA→PRODUCCION, REENCAUCHADA/REPARADA/RECHAZADA→PLANTA, REPROCESO→PRODUCCION)
- `COMBINACIONES_VALIDAS` (R1-R6): validación de combinaciones estado↔ubicación
- Regla R5: estado `REPARADA` solo con diseño de banda `REP`
- `crear()` asigna ubicación inicial `PLANTA` + historial inicial
- Eliminado bypass `LlantaRepository.update_estado()`

#### UI
- Botón **INSPECCIÓN FINAL** en módulo Producción: veredicto rápido por tiquete con veredictos alcanzables desde el estado actual
- Botón **CAMBIO DE UBICACIÓN** en módulo Planta: movimiento validado por combinaciones estado↔ubicación
- Dropdowns de reportes ahora usan `ESTADOS_PROCESO`/`UBICACIONES_PLANTA` (sin hardcode)

#### Reportes/KPIs
- Centralizadas las copias de `ESTADOS_EN_PLANTA` (dashboard, reportes, clientes)
- Nueva constante `ESTADOS_EN_PRODUCCION` (APTA + REPROCESO) para KPIs de producción
- Nueva constante `ESTADOS_TERMINADAS` (REENCAUCHADA + REPARADA) para inventario
- KPI "en producción" cuenta por ubicación `PRODUCCION` (fuente de verdad)

### Changed
- Migración BD v2.5.0: CHECK constraints de 6 estados en `llantas` y `estados_llanta`; DEFAULT `PLANTA` en `ubicacion_actual`
- Corrección de datos: PENDIENTE+PRODUCCION → APTA/PLANTA; ubicaciones NULL → PLANTA
- `config.py`: resolución de ruta unificada — el exe usa la BD del proyecto cuando está en `dist/`, o crea la suya propia si es portable; respeta `.env` (`DATABASE_URL`)
- Registro de migración v2.5.0 en `_migrations` vía `run_migration()` idempotente + `main.py`
- **Instalación limpia auto-inicializante**: en primera ejecución, el exe crea la BD con migraciones, admin (`admin/admin123`), datos maestros (marcas/medidas/diseños/productos/precios/causas/recetas) y reglas de automatización — no requiere copiar `delca.db`
- `src/database/registry.py`: añadidos `Permiso`/`rol_permiso` (faltaban para instalaciones limpias)
- `installer.iss`: onefile `DELCA ERP.exe` (v2.5.0), sin copia de BD
- **Fix backup automático**: `was_backup_done_today()` comparaba `YYYY-MM-DD` contra el nombre `YYYYMMDD` → nunca detectaba el backup del día → creaba backups duplicados en cada apertura. Ahora genera la clave con el formato correcto (1 backup diario)
- **Scheduler de backup robusto**: crea el backup del día **al arrancar la app** (no solo recordatorio) + timer de 6h como red de seguridad para el cambio de día; avisa solo si falla
- **Veredictos fijos de inspección final**: el diálogo INSPECCIÓN FINAL muestra siempre las 4 opciones `REENCAUCHADA | RECHAZADA | REPARADA | REPROCESO`; `APTA → RECHAZADA` añadido a la matriz de transiciones (nueva constante `VEREDICTOS_INSPECCION_FINAL`)
- **Ubicaciones fijas de cambio manual**: el diálogo CAMBIO DE UBICACIÓN (módulo Planta) muestra siempre las 2 opciones `CLIENTE | PLANTA` (nueva constante `UBICACIONES_CAMBIO_MANUAL`); la validación según el estado la sigue haciendo el servicio
- **Migración principal de llantas**: cargadas **24,451 llantas** desde `Llantas 18-08.csv` (ETL MAE_PROD.DBF) — el importador rechaza combinaciones estado+ubicación inválidas (reglas R1-R6) y las registra en `llantas no migradas.csv` (79 llantas: 56 REENCAUCHADA+PRODUCCION, 12 APTA+CLIENTE, 9 REPARADA+PRODUCCION, 2 PENDIENTE+CLIENTE); crea catálogos faltantes automáticamente (25 marcas, 54 dimensiones, 29 diseños)

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
