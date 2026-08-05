# DELCA ERP — Reglas de Negocio

## Módulo: Usuarios / Autenticación

### Autenticación
1. **Login**: Busca usuario por `username`. Verifica password con
   `bcrypt.checkpw(password.encode(), hash.encode())`. Si no coincide,
   login falla.
2. **Bootstrap admin**: En primera ejecución (0 usuarios en BD), crea
   rol 'ADMIN' y usuario 'admin' con password 'admin123'. Usa SHA-256
   pre-hash + bcrypt.
3. **Unicidad username**: Restricción UNIQUE en columna `username`.
4. **Sin gestión de sesiones**: El objeto usuario se pasa directamente
   al constructor de MainWindow. No hay tokens, cookies, ni timeouts.
5. **Sin RBAC en vistas**: El rol (`rol_id`) existe en BD pero ninguna
   vista valida permisos. Todos los usuarios ven todos los módulos.

---

## Módulo: Clientes

### Gestión de Clientes
1. **Campos obligatorios**: `nombre` y `nit`. Validación en service
   antes de insert.
2. **NIT único**: Restricción UNIQUE en BD. El service verifica
   duplicados antes de crear/actualizar.
3. **Clasificación ABC**: Columna `categoria_abc` (A, B, C). Default 'B'.
4. **Saldo automático**: `cliente.saldo` se actualiza en cada operación:
   - Factura creada: `+= total`
   - Pago registrado: `-= valor`
   - Factura anulada: `-= saldo_restante`
5. **Borrado lógico**: `activo = False` mantiene el registro en BD.
6. **Búsqueda**: Por nombre, NIT, teléfono, email con `ILIKE`.

---

## Módulo: Llantas

### Máquina de Estados (Trazabilidad)

```
RECIBIDA → INSPECCIÓN → PRODUCCIÓN → RASPADO → LLENADO →
VULCANIZACIÓN → TERMINADO → ENTREGADA
```

1. **Avance solo hacia adelante**: Validado por índice numérico en
   LlantaViewModel. No se puede retroceder.
2. **Sin saltos**: No se puede pasar de RECIBIDA a TERMINADO
   directamente. Cada estado intermedio es obligatorio.
3. **Estado terminal**: ENTREGADA. No hay transiciones posteriores.
4. **Código único**: `codigo` con UNIQUE constraint.
5. **Cliente opcional**: `cliente_id` nullable (FK a cliente).
6. **Historial completo**: Cada cambio de estado crea un registro en
   `estados_llanta` con timestamp.
7. **Historial de ubicaciones**: Cada movimiento físico crea un
   registro en `ubicaciones_llanta` con timestamp.
8. **Display states**: EN_BODEGA, EN_PRODUCCION, EN_ENTREGA son
   agrupaciones visuales, no estados reales en BD.

---

## Módulo: Finanzas

### Facturación

1. **Numeración automática**: Formato `FAC-NNNN` (FAC-0001, FAC-0002).
   El último número se determina por `id` descendente de facturas con
   prefijo `FAC-`. Fallback a 1 si hay error de parseo.
2. **Total > 0**: Validación estricta. Error: "El total debe ser mayor
   a cero".
3. **Cliente existente**: Debe existir en BD. Error: "Cliente no
   encontrado".
4. **Saldo inicial**: `factura.saldo = total`. `cliente.saldo += total`.
5. **Estados**: PENDIENTE → (pago total) → PAGADA. Ó → ANULADA.

#### Pagos
6. **Monto positivo**: `valor > 0`. Error si <= 0.
7. **Factura no anulada**: Rechazar pago en factura ANULADA.
8. **Factura no pagada**: Rechazar pago en factura ya PAGADA.
9. **No exceder saldo**: `valor <= factura.saldo`. Error: "El pago
    supera el saldo pendiente".
10. **Post-pago**: `factura.saldo -= valor`. Si `saldo == 0`,
    `factura.estado = 'PAGADA'`. `cliente.saldo -= valor`.
11. **Métodos**: EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE, OTRO.

#### Anulación
12. **No anular ya anulada**: Error si ya está ANULADA.
13. **No anular pagada**: Error si ya está PAGADA.
14. **Post-anulación**: `factura.estado = 'ANULADA'`.
    `cliente.saldo -= factura.saldo` (revierte saldo remanente).

### Cartera

1. **Filtro**: Solo clientes activos (`activo = True`).
2. **Cálculo**: SUM de `Factura.saldo` donde `estado = 'PENDIENTE'`.
3. **Exclusión saldo cero**: Clientes con `total_pendiente = 0` no
   aparecen en cartera.
4. **Antigüedad**: `(hoy - fecha_emision).days`:
   - 0-30 días: "0-30"
   - 31-60 días: "31-60"
   - 61-90 días: "61-90"
   - 91+ días: "90+"
5. **Color de fila**: Por rango de antigüedad (más oscuro = más vencido).

---

## Módulo: Inventario

### Productos

1. **Campos obligatorios**: `nombre`, `sku`.
2. **SKU**: Se guarda en mayúsculas (`sku.strip().upper()`). Único.
3. **Categorías del sistema**: MATERIA_PRIMA, INSUMOS, HERRAMIENTAS,
   REPUESTOS, EMPAQUES, OTROS.
4. **Stock**: Numeric(12,2), default 0.
5. **Borrado lógico**: `activo = False`.
6. **Unidad medida**: Default "UNIDAD", auto-mayúsculas.
7. **Stock inicial**: Si `stock_inicial > 0`, crea automáticamente un
   movimiento ENTRADA con referencia "INVENTARIO_INICIAL".

### Movimientos (Kardex)

1. **Tipos válidos**: ENTRADA, SALIDA, MERMA, AJUSTE.
2. **Cantidad >= 0**: Para ENTRADA/SALIDA/MERMA: debe ser > 0. Para
   AJUSTE: puede ser 0 (set absoluto).
3. **Stock suficiente**: SALIDA/MERMA requieren `cantidad <= stock`.
   Error: "Stock insuficiente: {stock}".
4. **Actualización de stock**:
   - ENTRADA: `stock += cantidad`
   - SALIDA: `stock -= cantidad`
   - MERMA: `stock -= cantidad`
   - AJUSTE: `stock = cantidad` (set absoluto)
5. **Costo**: Si no se especifica, usa `producto.costo_unitario`
   actual.
6. **Kardex**: Últimos 50 movimientos, orden descendente por fecha.
7. **Resumen**: Total productos, total unidades, valor inventario
   (stock * costo), count de stock bajo (< 10, > 0).

---

## Módulo: Automatización

### Reglas por Defecto (creadas en primera ejecución)

| Regla | Tipo | Nivel | Config |
|---|---|---|---|
| Stock Bajo | STOCK_BAJO | WARNING | umbral=10 |
| Cartera Vencida 30+ | CARTERA_VENCIDA | WARNING | dias=30 |
| Cartera Vencida 60+ | CARTERA_VENCIDA | CRITICAL | dias=60 |
| Llantas Listas para Entrega | LLANTAS_LISTAS | INFO | {} |

### Motor de Reglas

1. **Evaluación**: Solo reglas activas (`activa = True`).
2. **STOCK_BAJO**: Productos activos con `0 < stock < umbral`.
3. **CARTERA_VENCIDA**: Facturas PENDIENTE con `saldo > 0` y
   `(hoy - emision).days >= dias`.
4. **LLANTAS_LISTAS**: Llantas con `estado = 'ENTREGADA'`.


### Alertas

1. **Deduplicación**: Antes de crear una alerta, verifica si existe
   una no leída del mismo `tipo + entidad_tipo + entidad_id`. Si
   existe, omite.
2. **Limpieza automática**: `limpiar_alertas(dias=30)` elimina alertas
   más antiguas que N días.
3. **Marcado**: Individual (`marcar_leida(id)`) o masivo
   (`marcar_todas_leidas()`).
4. **Conteo**: `alertas_no_leidas_count()` para badges de notificación.

---

## Módulo: Reportes

### Clientes
- Por ciudad (agrupado)
- Activos vs inactivos
- Mayor saldo (top 5)

### Llantas
- Por estado (agrupado)
- Por cliente (agrupado)
- Tiempo promedio de producción (días de RECIBIDA a TERMINADO)

### Finanzas
- Facturación por mes (SUM total por mes)
- Pagos por método (conteo)
- Facturas por estado (conteo)

### Inventario
- Productos por categoría (conteo)
- Movimientos por tipo (conteo)
- Stock bajo (productos con `0 < stock < 10`)

---

## Módulo: Auditoría

**ESTADO**: Modelo existe pero **no implementado**.

1. **Acciones definidas**: CREATE, UPDATE, DELETE, LOGIN, LOGOUT.
2. **Campos**: usuario_id, entidad, accion, detalle, payload_json,
   ip_origen, fecha.
3. **Sin servicio**: No hay `AuditoriaService`. No hay hooks ni
   decoradores que automaticen el registro.
4. **Sin UI**: No hay vista en el sidebar. No se pueden consultar
   logs desde la interfaz.
5. **Consecuencia**: La tabla `auditoria` permanece vacía. No hay
   trazabilidad de cambios en producción.

---

## Dashboard (KPIs)

| Métrica | Fórmula |
|---|---|
| Total Clientes | `COUNT(cliente)` |
| Clientes Activos | `COUNT(cliente WHERE activo = True)` |
| Total Llantas | `COUNT(llantas)` |
| En Producción | `COUNT(llantas WHERE estado IN ('PRODUCCION','INSPECCION'))` |
| Entregadas | `COUNT(llantas WHERE estado = 'ENTREGADA')` |
| Recibidas | `COUNT(llantas WHERE estado = 'RECIBIDA')` |
| Facturación del Mes | `SUM(total) WHERE fecha_emision >= inicio_de_mes` |
| Cartera Pendiente | `SUM(saldo) WHERE saldo > 0` |
| Total Facturas | `COUNT(facturas)` |
| Facturas Pendientes | `COUNT(facturas WHERE estado = 'PENDIENTE')` |
| Actividad Reciente | Últimos 10 cambios de estado en llantas |
| Llantas por Estado | GROUP BY estado |
