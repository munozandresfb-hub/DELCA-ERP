# Notas de Migración desde el Sistema Legacy (MAE_PROD)

> Lecciones aprendidas de la migración 2026 — **léelas antes de cualquier futura migración**.

## ✅ Regla #1c: Verificar el identificador contra el valor IMPRESO en el artículo físico

**Lección (septiembre 2026):** el MAE_PROD almacena por llanta DOS campos de tiquete:
- `TIQUETE` ('J1353') — número de **secuencia interna** del registro (con prefijo J)
- `TIQUETE2` ('1355') — el **tiquete REAL**, el impreso en la llanta física

La migración original guardó `TIQUETE` → los tiquetes no coincidían con las llantas físicas
ni con el programa origen (verificado: O.S. 577-1 = tiquete 1355, no 1353). Corregido con
`scripts/corregir_tiquetes.py` (24,450 llantas, backup `delca_pre_tiquetes_*.db`).

**Regla:** para cualquier migración, verificar el identificador contra el **valor impreso en el
artículo físico** (o contra el programa origen en uso), NO contra el primer campo con nombre
similar del DBF. Los sistemas legacy suelen tener campos de secuencia interna junto al
identificador real. Un tiquete/identificador "que no coincide" es señal de campo equivocado.

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

## Correcciones aplicadas (2026-09-14/15)

1. **Costos**: `scripts/corregir_costos_produccion.py` — 24,304 llantas alineadas al catálogo de Facturación-Precios (fuente manual del negocio). Backup: `backups/delca_pre_costos_*.db`.
2. **Clientes**: `scripts/corregir_clientes_nit.py` — 4,196 llantas realineadas por NIT (0 ambigüedades). Backup: `backups/delca_pre_clientes_20260914_163911.db`.
3. **Tiquetes**: `scripts/corregir_tiquetes.py` — 24,450 llantas realineadas al tiquete real (`TIQUETE2` del MAE_PROD, el impreso en la llanta; sin prefijo J). Backup: `backups/delca_pre_tiquetes_*.db`. La excepción `J23489` era una llanta **duplicada** (misma llanta existía como 24922) → eliminada por orden del negocio.
4. **18 llantas con NIT vacío en legacy**: `scripts/aplicar_clientes_validados.py` — cliente asignado manualmente por el negocio (ROSELLANTAS LTDA, ROBERTO LOPEZ, GIRALDO RIVERA, PEREZ ABELINO, GERARDO BRAVO, TORO JOSE DOMINGO) + **4 NITs reales corregidos** (los previos derivados del código legacy: 0301→005824600, 0135→0025865400, 060→0025845600, 07213518→901585099). Backup: `backups/delca_pre_clientes_validados_20260915_102656.db`.
5. **NO unificados** (decisión del negocio): 11 grupos (318 llantas) donde el nombre legacy existe en DELCA con otro NIT — se dejan como quedaron (por NIT), sin mover ni fusionar.

## Pendientes de validación del negocio (2026-09-15)

1. **15 llantas sin cliente**: 9 antiguas (6659, 8251, 9588-90, 12491-92, 12516-17) sin código en el legacy + 6 recientes (25042-45 O.S. 10545, 25064-65 O.S. 10614) con códigos huérfanos C4872/C4873 (no existen en MAE_CLIENTE ni en el CSV de clientes). Análisis agotado (COMPRADOR/FACTURA/PRECIO vacíos, sin contexto inferible). Lista: `completar_clientes_15_2026-09-15.csv`.
2. **117 clientes con NIT sospechoso** (<5 dígitos): **data sucia del sistema legacy** (verificado: el MAE_CLIENTE ya tenía esos NITs — 73/117 iguales al origen; 54 usan el código como NIT). **Decisión del negocio (2026-09-15): SE DEJAN COMO VIENEN DEL LEGACY, sin corregir.** Lista de referencia: `nits_sospechosos_2026-09-15.csv`.

## Verificación de consistencia (2026-09-15)

- 24,450 llantas · 0 tiquetes duplicados · 0 con prefijo J · 0 cliente_id huérfanos · 0 historiales huérfanos
- 24,304 llantas con costo · 15 sin cliente (pendientes) · 5,239 clientes
- Integridad referencial completa (orden/dimensión/marca/fecha 100% alineados con MAE_PROD)