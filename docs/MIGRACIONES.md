# Notas de Migración desde el Sistema Legacy (MAE_PROD)

> Lecciones aprendidas de la migración 2026 — **léelas antes de cualquier futura migración**.

## ✅ Regla #1b: NO unificar clientes por coincidencia de NIT (ni por nombre)

**Lección adicional (septiembre 2026):** aunque dos registros (legacy y DELCA) compartan el mismo NIT,
**no asumir que son la misma persona/empresa ni unificarlos**. La decisión de unificar es del negocio.
- El NIT es una llave para *asignar* llantas, pero NO para *fusionar* clientes: personas/empresas
  distintas pueden compartir NIT en los datos migrados, y unificar causa errores de conteo
  (ej. RIVERA MANUEL vs RIVERA FAJARDO: el conteo por NIT decía 6, la verificación manual mostró 7).
- **Dejar los datos como vienen de la migración** (no mover llantas entre clientes por nombre/NIT
  sin validación explícita del negocio).
- Cuando un conteo por NIT no cuadre con la verificación manual, **confiar en la verificación manual**.

## ⚠️ Regla #1: NUNCA usar ids autoincrementales del destino ni ids numéricos derivados del origen

**Problema real encontrado (septiembre 2026):**
- `MAE_CLIENTE.DBF` identifica a los clientes con `COD_CLIEN`, una **CADENA** (`'98'`, `'C453'`, `'5.236.034'`), NO un número secuencial.
- La migración original insertó los clientes en `cliente` **sin id explícito** → SQLite asignó ids secuenciales (1..N).
- El ETL que generó el CSV de llantas convirtió `COD_CLIEN` a un número con **corrimientos por bloque** (por clientes omitidos/duplicados en el camino).
- Resultado: **4,196 llantas (17%) apuntaban a un cliente existente pero EQUIVOCADO** — invisible a simple vista porque los ids eran válidos.

**Regla:** al relacionar registros migrados, usar SIEMPRE la **llave natural** (NIT/cedula/código de negocio). Nunca confiar en:
- ids autoincrementales del destino,
- posiciones/índices de archivo,
- conversiones numéricas de códigos alfanuméricos del origen.

## ✅ Regla #2: Verificar SIEMPRE contra el origen, registro a registro

- Comparar el destino contra el **DBF origen** (no contra el CSV intermedio — el ETL pudo introducir el error).
- Resolver la llave natural en AMBOS lados y comparar el resultado (ej. tiquete → COD_CLIEN → NIT → cliente).
- La verificación debe dejar **0 discrepancias** (o lista explícita de excepciones justificadas).

## ✅ Regla #3: Preservar los códigos originales en la migración

- Si el origen tiene un código (aunque sea alfanumérico), **conservarlo como columna** (`codigo_legacy`) al migrar — facilita auditorías y correcciones.
- Migrar clientes por NIT: el NIT del origen (`MAE_CLIENTE.NIT_CLIEN`) debe quedar como llave.

## ✅ Regla #4: Chequear referencias huérfanas

- `MAE_PROD.COD_CLIEN` que no existe en `MAE_CLIENTE` (ej. `C4872`, `C4873`) = referencias huérfanas → listar y resolver manualmente.
- `MAE_CLIENTE` con NIT vacío = no verificable por NIT → resolver por nombre con validación del negocio.

## ✅ Regla #5: Usar el patrón de scripts de corrección

Todo script de corrección de datos debe tener:
1. `--dry-run` (reporta impacto sin escribir),
2. backup automático antes de `--ejecutar`,
3. verificación post-corrección contra el origen.

Ver: `scripts/corregir_clientes_nit.py` y `scripts/corregir_costos_produccion.py` (ejemplos del patrón).

## Archivos clave del origen (carpeta DELCA)

| Archivo | Contenido | Llaves |
|---|---|---|
| `MAE_PROD.DBF` | 24,530 llantas | `TIQUETE`, `ORDEN`, `CONSEC`, `COD_CLIEN` |
| `MAE_CLIENTE.DBF` | 5,236 clientes | `COD_CLIEN` (string), `NIT_CLIEN`, `DESC_CLIEN` |
| `MAE_MARCA.DBF` / `MAE_TIPO.DBF` | catálogos | códigos |
| `Clientes 1 18-08.csv` | clientes exportados | nit |
| `Llantas 18-08.csv` | llantas exportadas (ETL) | tiquete, cliente_id (⚠️ desalineado) |

## Correcciones aplicadas (2026-09-14)

1. **Costos**: `scripts/corregir_costos_produccion.py` — 24,305 llantas alineadas al catálogo de Facturación-Precios (fuente manual del negocio). Backup: `backups/delca_pre_costos_*.db`.
2. **Clientes**: `scripts/corregir_clientes_nit.py` — 4,196 llantas realineadas por NIT (0 ambigüedades). Backup: `backups/delca_pre_clientes_20260914_163911.db`.
3. **Pendientes de validación del negocio** (NO aplicadas): 18 llantas con NIT vacío en legacy y nombre distinto (el negocio decidió NO asignar por nombre — se mantienen en el cliente asignado por NIT); 15 llantas sin cliente (7 con códigos huérfanos C4872/C4873, 8 sin código). Detalle: `verificacion_clientes_POST_2026-09-14.csv`.
4. **NO unificados** (decisión del negocio): 11 grupos (318 llantas) donde el nombre legacy existe en DELCA con otro NIT — se dejan como quedaron (por NIT), sin mover ni fusionar.
5. **Pendientes de validación del negocio**: 15 llantas sin cliente (7 con códigos huérfanos C4872/C4873, 8 sin código). Detalle: `verificacion_clientes_POST_2026-09-14.csv`.