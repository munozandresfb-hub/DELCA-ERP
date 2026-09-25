# DELCA ERP — Reporte Forense de Estabilidad

**Fecha:** 23 de septiembre de 2026
**Alcance:** Investigación forense sobre la estabilidad operativa del sistema DELCA ERP (Reencauchadora DELCA SAS)
**Objetivo:** Identificar riesgos de estabilidad, evidenciar el comportamiento real en producción y proponer un plan de mejora priorizado.

---

## 1. Resumen Ejecutivo

DELCA ERP es un sistema de escritorio Windows (Python 3.13 + PySide6 + SQLAlchemy 2.0 + SQLite WAL) en uso productivo desde ~junio 2026, con **24.450 llantas, 5.241 clientes y 1.071 eventos de auditoría** en su base de datos. Los **178 tests automáticos pasan** y la **integridad de la BD es correcta** (PRAGMA integrity_check = ok, 0 violaciones de FK).

Sin embargo, la investigación forense revela **4 problemas graves de estabilidad** que comprometen la operación:

1. **ARQUITECTURA DE BD INVÁLIDA PARA MULTI-USUARIO** — La base de datos SQLite (WAL) vive en una carpeta OneDrive sincronizada y es accedida por 2-3 usuarios en red. SQLite WAL no funciona sobre filesystem de red/sync; el riesgo de corrupción silenciosa y pérdida de datos es cuestión de tiempo (ver hallazgo E-0).
2. **OBSERVABILIDAD NULA** — El archivo de log de producción tiene **0 bytes tras 91 días de uso activo**. Cualquier error que ocurra en operación se pierde sin dejar rastro.
3. **RACE CONDITION EN BACKUPS** — Evidencia de 6 backups creados en el mismo segundo. La retención de 30 backups se consume en ~5 días.
4. **BUGS CONCRETOS DE CÓDIGO** — Un crash garantizado en exportación de tablas vacías, timeouts de sesión que nunca aplican como se documentó, y estados inconsistentes que se reportan como éxito al usuario.

**Calificación general de estabilidad: CONDICIONAL / NO FALSIFICABLE.** No se puede afirmar que el sistema sea estable ni inestable con la evidencia actual, porque el sistema no registra sus propios fallos. La corrección del logging es un prerrequisito para cualquier garantía de estabilidad.

---

## 2. Metodología

| Técnica | Detalle |
|---|---|
| Análisis estático | 156 archivos Python en `src/`, 30+ scripts en `scripts/`, 11 vistas Qt |
| Auditoría de logs | `logs/delca.log` + copia empaquetada `dist/logs/delca.log`, rotaciones, `error_output.txt` |
| Ejecución de tests | `pytest` — 178 passed, 254 warnings (DeprecationWarning de `datetime.utcnow()`) |
| Verificación de BD | PRAGMA integrity_check, foreign_key_check, quick_check, journal_mode, user_version |
| Inspección de backups | 30 archivos `.db` en `backups/`, timestamps, distribución por día |
| Auditoría de BD | Conteo de tablas, usuarios, roles, eventos de auditoría, estado de migraciones |
| Revisión de configuración | `.env`, `config.py`, `engine.py`, `main.py`, mecanismos de backup/sesión |

---

## 3. Estado del Sistema en Producción

### 3.1 Base de datos — SALUDABLE

| Verificación | Resultado |
|---|---|
| PRAGMA integrity_check | **ok** |
| PRAGMA foreign_key_check | **0 violaciones** |
| PRAGMA quick_check | **ok** |
| PRAGMA journal_mode | **wal** |
| Tamaño | 8.96 MB |
| Última modificación | 23/09/2026 16:37 (uso activo) |

### 3.2 Migraciones — APLICADAS EN ORDEN

13 migraciones registradas en tabla `_migrations`, en orden cronológico correcto (v1.0.0 → v2.8.1), entre 22/07/2026 y 02/09/2026. El mecanismo de migración única (`run_migration_once`) funciona.

### 3.3 Tests — 178 PASSED

La suite de tests cubre: auth, backup, audit, session, permisos, productos, precios, llantas, facturas, reportes. **254 warnings** de deprecación (`datetime.utcnow()`), que indican código legacy pendiente de modernizar.

### 3.4 Volumen de datos

| Tabla | Filas |
|---|---|
| llantas | 24.450 |
| estados_llanta | 24.472 |
| ubicaciones_llanta | 24.478 |
| cliente | 5.241 |
| auditoria | 1.071 |
| alertas | 833 |
| marcas_llanta | 476 |
| precios_producto | 449 |

---

## 4. HALLAZGOS CRÍTICOS

### 🔴 E-0. Arquitectura de BD inválida: SQLite WAL en OneDrive compartido (CRÍTICO — riesgo sistémico)

**Evidencia:**
- `delca.db` (8.96 MB, WAL mode) reside en `C:\Users\andre\OneDrive\Escritorio\DELCA\Programacion DELCA v2\` — carpeta **sincronizada por OneDrive**.
- La app corre en **2-3 equipos** en red local que abren la misma BD simultáneamente (evidencia: 6 backups en el mismo segundo = múltiples instancias concurrentes).
- Los 178 tests pasan y `integrity_check = ok` **en la copia local auditada** — pero eso no valida las otras copias ni el futuro.

**Por qué es inválido (SQLite no fue diseñado para esto):**
1. **Sin locks distribuidos**: OneDrive no ofrece byte-range locks entre máquinas → dos escritores simultáneos son invisibles entre sí → *last-writer-wins* por archivo.
2. **Conflictos de sync**: OneDrive renombra al perdedor (`delca (1).db`) → **divergencia silenciosa**; cada PC sigue operando su copia local sin saberlo.
3. **WAL es intrínsecamente local**: el archivo `-shm` es memoria compartida entre procesos del mismo host. SQLite documenta que **WAL no funciona sobre filesystem de red**. Sincronizar el `.db` sin su `-wal` = transacciones comprometidas perdidas; sincronizar `-shm`/`-wal` entre máquinas = corrupción.
4. **Subidas parciales (torn)**: otra máquina puede abrir un `.db` a medio subir.
5. **Checkpoint**: reescribe el `.db` in situ mientras el sync lo sube → snapshots inconsistentes.
6. **Files On-Demand**: hidratación/deshidratación de la BD; fallos de apertura offline.

**Impacto:** Pérdida silenciosa de datos, corrupción y divergencia entre equipos. Es el riesgo de mayor impacto de todo el sistema. No hay mitigación aceptable sobre OneDrive (ni lock files: heredan el mismo problema).

**Remediación (proyecto, 2-4 días):**
- Migrar a BD cliente-servidor en un PC del taller que actúe de servidor: **PostgreSQL** (fit natural con SQLAlchemy, sin límites, gratis) o SQL Server Express (si prefieren tooling Microsoft). Con 9MB y 3 usuarios, cualquiera sobra.
- **Patrón correcto para OneDrive**: que sincronice los *backups* (dumps diarios), no la BD viva.
- **Interino si la migración tarda >2 semanas**: sacar la BD de la carpeta sincronizada a un share SMB en un PC + `journal_mode=DELETE` + `busy_timeout` (WAL no funciona por red). Mitiga, no elimina.
- Preparación de la migración: normalizar los 35 `datetime.now()` naive a timezone-aware (prerequisito de tipos de fecha en PostgreSQL).

---

### 🔴 E-1. Observabilidad nula — log de producción vacío (CRÍTICO)

**Evidencia:**
- `logs/delca.log` = **0 bytes**, mtime 24/06/2026 16:08 (día de creación del handler).
- `dist/logs/delca.log` (copia del .exe) = **0 bytes**, mtime 24/08/2026.
- **No existen rotaciones** (`delca.log.1/.2/.3`).
- La app se usa intensivamente: 30 backups, BD modificada hoy, binario recompilado hoy.
- **91 días de operación con cero líneas de log.**

**Causa raíz (probable, requiere verificación en vivo):**
1. El root logger está en `WARNING` (`engine.py:25`) y casi todo el código reporta errores con `print()` (se pierde en `pythonw`, que no tiene consola). Ver `main.py:125,140` — errores de migración y datos maestros se imprimen y se **ignoran** (la app continúa con BD potencialmente inconsistente).
2. Posible reset del root logger por una librería externa (handler añadido al importarse `engine.py`, puede perderse si algo llama `logging.basicConfig()` después).

**Impacto:**
- No se puede medir tasa de errores, ni detectar fallos de BD, backups, logins o migraciones.
- **Cualquier afirmación de "estabilidad" es no-falsificable** con la evidencia actual.
- Los errores de migración se ignoran silenciosamente: `main.py:124-125` imprime y continúa.

**Acción inmediata (15 min):** Lanzar la app, intentar un login fallido, esperar, salir y re-verificar `delca.log`. Si sigue en 0 bytes → bug confirmado de logging. Si crece → el problema es que no hay eventos (información igualmente valiosa).

---

### 🔴 E-2. Race condition en el sistema de backups (ALTO)

**Evidencia:**
- **6 archivos de backup creados en el mismo segundo** (16:40:52.xxx) el 23/09/2026.
- Patrón repetido: 6 backups en 12:17, múltiples en 11:09, múltiples en 09:26.
- Solo **5 días distintos** con backups entre 16/09 y 23/09 (30 archivos, retención llena).

**Causa raíz:**
- `was_backup_done_today()` es **check-then-act sin lock** (`backup_service.py:340-351`).
- Se dispara desde **3 puntos**: arranque de MainWindow +3s (`main_window.py:278`), timer cada 6h (`main_window.py:275`), apertura de BackupView +5s (`backup_view.py:53`).
- Con 2-3 usuarios en red local abriendo la app a la misma hora (inicio de jornada), **todas las instancias pasan el check simultáneamente** y crean backups redundantes.

**Impacto:**
- **Retención consumida en días, no semanas**: con 6 backups/día, los 30 slots se llenan en 5 días. La cobertura de recuperación retrocede a solo ~1 semana.
- `create_backup()` es **síncrono en el hilo de UI**: congela la interfaz durante el WAL checkpoint + copia (~8.5 MB).
- Los backups exitosos se reportan con `print()` (invisibles en producción).

**Acción inmediata:** Implementar un lock de archivo (ej. `msvcrt.locking` o archivo `.backup.lock`) y/o centralizar la decisión de "backup del día" con verificación post-creación.

---

### 🔴 E-3. Bug de crash garantizado: exportación CSV de tabla vacía (ALTO)

**Evidencia:** `backup_service.py:229-242` — `export_to_csv()`:

```python
rows = conn.execute(f"SELECT * FROM [{table}]").fetchall()
finally:
    conn.close()          # ← conexión CERRADA aquí

if not rows:
    Path(output_path).write_text(
        ",".join(f'"{col}"' for col in [d[0] for d in conn.execute(   # ← conn YA CERRADA
            f"PRAGMA table_info([{table}])"
        ).fetchall()])
        ...
```

**Impacto:** Si una tabla está vacía (p. ej. `costos_produccion_estandar`, `facturas`, `pagos` — **0 filas en producción hoy**), la exportación lanza `sqlite3.ProgrammingError: Cannot operate on a closed database`. La excepción se captura y devuelve `(False, "CSV export failed: ...")`, pero el error queda sin loguear y la exportación falla de forma confusa para el usuario.

---

### 🟠 E-4. Timeouts de sesión por rol que nunca aplican (MEDIO — no ALTO)

**Evidencia:** `session_service.py:27-31`:

```python
ROLE_TIMEOUTS = {
    "ADMIN": 1800,           # 30 min
    "Gerencia": 10800,       # 3 horas   ← capitalización incorrecta
    "Operador": None,        # sin cierre ← capitalización incorrecta
}
```

Pero los roles reales en BD (`bootstrap_admin.py:14`) son **"GERENCIA"** y **"OPERADOR"** (mayúsculas). `ROLE_TIMEOUTS.get("GERENCIA", fallback)` devuelve el fallback de **30 minutos**.

**Impacto (falla en dirección restrictiva):**
- Un usuario de Gerencia se desconecta a los **30 minutos** (en vez de 3 horas).
- Un Operador se desconecta a los **30 minutos** (en vez de "sin cierre").
- Con todos los usuarios ADMIN hoy, y sin entrada "ADMIN" en el dict, **todos caen al default de 30 min**.
- Es una molestia UX (cierres de sesión frecuentes), no un riesgo de seguridad (falla más restrictivo, nunca más permisivo). **Severidad: MEDIO.**

**Causa raíz sistémica:** los nombres de rol se comparan por strings sin constante única de verdad. Se corrige centralizando los nombres de rol en constantes/Enum (prerequisito también del RBAC).

---

### 🔴 E-5. Estados inconsistentes reportados como éxito (ALTO)

**Evidencia:** `usuarios_view.py:525-537` — al reactivar un usuario:

```python
except Exception:
    session.rollback()
finally:
    session.close()
# ...
self._mostrar_mensaje("success", "Usuario reactivado")   # ← se muestra SIEMPRE
```

**Impacto:** Si el commit falla (lock de BD, constraint), el usuario ve "Usuario reactivado" aunque el cambio **no se guardó**. Estado inconsistente sin detección. Patrón a replicar en auditoría de todos los handlers de CRUD.

---

### 🟠 E-6. Configuración de impresión falla silenciosamente (MEDIO)

**Evidencia:** `tiquete_printer.py:77` — lectura de config JSON falla → devuelve defaults `(0.0, 0.0, {})` sin aviso. Línea 86: `CONFIG_PATH.write_text(...)` sin try/except.

**Impacto:** La calibración de impresión de tiquetes se **desincroniza silenciosamente** → tiquetes mal impresos (offsets incorrectos) sin diagnóstico posible. Crítico porque la impresión de tiquetes es un proceso central del negocio.

---

## 5. Patrones Sistémicos de Fragilidad

| Patrón | Conteo | Riesgo | Ejemplos representativos |
|---|---|---|---|
| `except: pass` (errores silenciados) | 11 | Medio | `kpi_historico_dialog.py:212` (render gráfico), `_llantas_reports.py:52,72,82` (filtros que no cargan), `_export.py:54` |
| `except` sin logging | ~25 | Medio-Alto | `usuarios_view.py:531`, diálogos kardex/inventario (Decimal parsing) |
| `print()` para errores (se pierde en pythonw) | 19 en 11 archivos | **Alto** | `main_window.py:190,210,286,289`, `inventario_view/_view.py:248-260` |
| DB en handlers de botón sin try/except | 9+ | **Alto** | `planta_view.py:189-198,410,436,515`, `produccion_view.py:166`, `_dialogs.py:97,343,655` |
| `.all()` sin límite en tablas grandes | ~30 | Medio-Alto | `factura_service/_facturas.py:42,84,127,167,221`, `cliente_repository.py:11`, `llanta_repository.py:13` |
| `datetime.now()` naive vs BD | 35 | Medio | `auth_service.py:81,102`, `login_user.py:61,106` (TypeError latente si BD cambia a aware) |
| `session.commit()` sin try/except en flujos UI | 16 | Medio | `login_viewmodel.py:35` (propaga al event-loop Qt) |
| Operaciones de archivo sin manejo de errores | ~5 | Medio | `tiquete_printer.py:86`, `backup_service.py:92` (unlink en prune) |
| `QMessageBox` con traceback expuesto | 0 | — | ✅ Sin exposición de stack al usuario (buena práctica) |

---

## 6. Evidencia de Producción (Datos Duros)

| Métrica | Valor | Interpretación |
|---|---|---|
| Días con backup (16-23 sept) | **5 de 7** | Backups NO se crean todos los días de uso |
| Backups en mismo segundo | **6** | Race condition confirmada (23/09 16:40:52) |
| Retención real cubierta | **~1 semana** | Con 30 backups multi-día, la cobertura se degrada |
| Intentos de login fallidos (auditoría BD) | **123** | Hay actividad de login fallida registrada (la auditoría BD sí funciona) |
| Logins exitosos (auditoría BD) | **369** | Uso real continuo desde 24/06/2026 |
| Eventos CREATE/UPDATE auditados | 101 / 102 | La auditoría de cambios funciona |
| `ip_origen` en auditoría | **Siempre NULL** | No se captura IP (limitado en app local, aceptable) |
| Registros de LOGOUT | 375 | Ciclos de sesión consistentes con logins |

**Conclusión sobre la BD de producción:** Los datos están sanos (integridad OK), la auditoría de eventos funciona, y las migraciones están al día. Los problemas están en la **capa de observabilidad y en los mecanismos de respaldo**.

---

## 7. Plan de Mejora Priorizado (validado por consultor de arquitectura)

**Principio de orden:** impacto no es el único eje — un crítico de 30 min va antes que un crítico de 3 días.

### Fase 1 — Día 1: matar riesgos críticos baratos

| # | Acción | Impacto | Esfuerzo |
|---|---|---|---|
| 1.1 | **Arreglar el logging**: `logging_setup.py` al inicio de `main.py` (ver receta abajo) | Desbloquea toda la observabilidad | 30-60 min |
| 1.2 | **Fix `export_to_csv`** (`backup_service.py:229-242`): re-abrir conexión o capturar headers antes del close | Elimina crash garantizado | 15 min |
| 1.3 | **Smoke test de arranque**: `logger.warning("DELCA boot OK")` en `main()` + verificación en vivo (login fallido → revisar log) | Confirma causa raíz del logging | 15 min |

### Fase 2 — Semana 1-2: el riesgo sistémico (la BD)

| # | Acción | Impacto | Esfuerzo |
|---|---|---|---|
| 2.1 | **Decidir y migrar la BD fuera de OneDrive** (PostgreSQL o SQL Server Express en un PC servidor). Incluye normalización de los 35 `datetime.now()` naive | Elimina el riesgo #1 de pérdida de datos | 2-4 días |
| 2.2 | **Interino si la migración tarda >2 semanas**: mover BD a share SMB + `journal_mode=DELETE` | Mitiga (no elimina) el riesgo de corrupción | 2 h |

### Fase 3 — Semanas 2-4: bugs correctos

| # | Acción | Impacto | Esfuerzo |
|---|---|---|---|
| 3.1 | **Lock de backup** (diseñar según destino de BD: advisory lock en PG; dedupe por día en el interino) + **backup en QThread** (no congelar UI) | Elimina race condition + congelamiento | 2-3 h |
| 3.2 | **Fix `ROLE_TIMEOUTS`**: constantes de rol (Enum) como única fuente de verdad + test | Timeouts correctos por rol | 30 min |
| 3.3 | **Fix `usuarios_view.py:531`**: verificar resultado del commit antes de mostrar éxito | Estado consistente | 30 min |
| 3.4 | **Fix `tiquete_printer.py:77,86`**: try/except + log + feedback UI | Impresión confiable | 30 min |

### Fase 4 — Mes 1-2: robustez sistémica

| # | Acción | Impacto | Esfuerzo |
|---|---|---|---|
| 4.1 | **Reemplazar `print()` por `logging`** en las 19 ocurrencias de vistas + redirect stdout/stderr al log (truco barato que captura los restantes) | Todo error visible en log | 2 h |
| 4.2 | **Envolver llamadas DB de handlers de UI** en try/except (9+ sitios) | Evita que un fallo de BD mate la UI | 3-4 h |
| 4.3 | **Paginación/limitación de `.all()`** en tablas grandes | Previene degradación de memoria | 4 h |
| 4.4 | **Migrar a `datetime` timezone-aware** (ya incluido en 2.1 para PG) | Elimina TypeError latente | 2-3 h |
| 4.5 | **Modernizar `datetime.utcnow()`** (254 warnings de deprecación) | Higiene | 1 h |
| 4.6 | **Monitoreo de backups**: alerta si no hay backup del día a las 20:00 | Protege la recuperación | 1 h |
| 4.7 | **Prueba de restauración trimestral documentada** + copia off-site de backups | Garantiza que la recuperación funciona | 1 h/trimestre |

### Receta del fix de observabilidad (validada por consultor)

Un módulo `logging_setup.py` (~40-60 líneas) importado como primera línea de `main.py`:
1. `RotatingFileHandler` (5MB × 5) a `%LOCALAPPDATA%\DELCA\logs\delca.log` — nunca junto al exe (Program Files es read-only) ni en OneDrive.
2. Root logger a INFO.
3. `sys.excepthook` = log del traceback completo + QMessageBox amable (destrona el `format_exc(limit=3)` del hallazgo 8).
4. **Redirigir `sys.stdout`/`sys.stderr` al log (tee)**: captura los 19 `print()` restantes sin tocarlos — crítico porque `pythonw` no tiene consola.
5. Migraciones: `raise` en fallo (abortar arranque) en vez de print+continue.
6. Bonus: ítem de menú "Abrir carpeta de logs" para soporte.

---

## 8. Huecos de Auditoría Pendientes (recomendaciones de verificación)

| Verificación | Por qué importa |
|---|---|
| **Modo de compartición real de OneDrive**: ¿sync en cada PC o SMB a carpeta dentro de OneDrive? Buscar copias de conflicto (`delca (1).db`, sufijos `-PC2`), si `-wal`/`-shm` se sincronizan, Files On-Demand activo | Cambia el modo de fallo de la BD |
| **Divergencia ya ocurrida**: comparar `COUNT(*)`/`MAX(id)` por tabla entre las copias locales de cada PC | Puede haber pérdida silenciosa previa no detectada |
| **Método de backup**: ¿`shutil.copy` cruda o `sqlite3` backup API / `VACUUM INTO`? ¿Se ha restaurado un backup alguna vez? ¿Viven los backups en la misma carpeta OneDrive? | Copia cruda de BD WAL pierde transacciones; backups en OneDrive se corrompen junto con la BD |
| **Estado de esquema tras migraciones ignoradas**: `_migrations` vs lo que el código espera | Migración fallida + app continúa = código nuevo sobre esquema viejo |
| **Event Viewer de Windows** (Application log) en las 3 máquinas + carpeta WER | Único registro de crashes de `pythonw` que existe hoy |
| **Version skew**: cómo se despliegan actualizaciones del exe a los 3 PCs | Versiones distintas compartiendo una BD = comportamientos divergentes |
| **Otras carreras check-then-act**: numeración de documentos/tiquetes (duplicados mismo segundo), doble-submit | El patrón de backups probablemente no es el único |
| **Entorno**: Defender/AV escaneando `.db`/`.wal` (SQLITE_BUSY intermitente), PRAGMAs (`busy_timeout`, `synchronous`), UPS en PCs de taller | Causas de bloqueos/corrupción no cubiertas por el código |

---

## 9. Riesgos No Cubiertos (recomendaciones de monitoreo)

- **Contratos de servicio**: no hay registro de SLA/backup externo. La única copia de la BD y sus backups vive en el mismo disco (OneDrive). Un ransomware o fallo de disco destruiría ambos. **Recomendación:** copia off-site (copia OneDrive ya parcialmente la cubre, pero los backups están en la misma carpeta).
- **Pruebas de restauración**: no hay evidencia de que se haya ejecutado una restauración de backup real en producción. **Recomendación:** prueba de restauración trimestral documentada.
- **Multi-instancia**: 2-3 usuarios escribiendo en la misma BD SQLite. WAL + busy_timeout=5000 mitiga parcialmente, pero el mecanismo de backup no está diseñado para concurrencia (ver E-2) y la arquitectura OneDrive es inválida para multi-usuario (ver E-0).

---

## 10. Veredicto

**El sistema funciona y sus datos están sanos, pero es opaco y su arquitectura de datos es frágil.** Tres frentes definen la estabilidad futura:

1. **La BD en OneDrive es un riesgo de pérdida de datos a mediano plazo** (E-0) — es el problema de mayor impacto y el primero a resolver con una migración a PostgreSQL/SQL Server en un PC servidor.
2. **La infraestructura de estabilidad (logging, backups, manejo de errores) tiene fallas silenciosas** que hoy no se detectan — restaurar la observabilidad es el prerequisito para diagnosticar todo lo demás.
3. **Los bugs correctos (export CSV, timeouts de rol, estados inconsistentes, impresión) son de bajo esfuerzo y se corrigen en días.**

Con las Fases 1-3 del plan, el sistema pasa de "no falsificable" a "verificablemente estable". Sin la migración de la BD (Fase 2), cualquier otra mejora sigue bajo la sombra del riesgo de corrupción/divergencia.