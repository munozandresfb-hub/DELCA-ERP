# DELCA ERP — Plan de Remediación Integral (Estabilidad + Seguridad)

**Fecha:** 23/09/2026
**Origen:** Hallazgos de `REPORTE_FORENSE_ESTABILIDAD.md` y `REPORTE_SEGURIDAD_HALLAZGOS.md` (auditoría del 23/09/2026, validada por consultor de arquitectura)
**Objetivo de implementación:** `C:\Users\andre\OneDrive\Escritorio\DELCA\Programacion DELCA v2\` (producción, versión 2.8.1)
**Regla de oro:** NINGÚN cambio de código toca la BD viva (`delca.db`) salvo el Lote 0 (remediación de datos, con backup previo obligatorio). Todo cambio se verifica con pytest + basedpyright + LSP antes de darse por cerrado.

---

## 0. Decisiones del negocio (RESUELTAS 23/09/2026 — COMPLETAS)

| ID | Decisión | Resolución | Estado |
|---|---|---|---|
| D1 | Destino de la BD | **(a) PostgreSQL en un PC del taller distinto al actual** — identificar equipo servidor antes del L8 | ✅ |
| D2 | ADMIN break-glass | **Andrés (`admin`)** · María José = GERENCIA | ✅ |
| D3 | Roles reales | 5 personas + Andrés, mapeo: María José→GERENCIA, Diana→GERENCIA, Adela→OPERADOR, Oscar→OPERADOR, Invitado→OPERADOR | ✅ |
| D4 | Política de contraseñas | **1 contraseña por rol (ADMIN/GERENCIA/OPERADOR), cambio obligatorio 1 vez al año (365 días)** | ✅ |
| D5 | Autorización datos | **Autorizado** — mostrar SQL antes de ejecutar | ✅ |
| D6 | Cifrado en reposo | **Suficiente con servidor protegido** (no SQLCipher) | ✅ |
| A1 | ADMIN definitivo | Andrés = ADMIN · María José = GERENCIA | ✅ |
| A2 | Roles del sistema | **NO crear roles nuevos.** Quedan solo ADMIN / GERENCIA / OPERADOR (sin VENTAS, sin CONTADOR, sin CONSULTA) | ✅ |
| A3 | Clave por rol | **Confirmado: 1 clave compartida por rol.** Riesgo de trazabilidad documentado y aceptado por el negocio | ✅ |

### ⚠️ Nota de decisión A3 (riesgo aceptado, documentado)

El negocio aceptó **clave compartida por rol**: todos los usuarios del mismo rol comparten la misma contraseña. Consecuencias aceptadas:
- La auditoría registra `usuario_id`, pero con clave compartida **no distingue quién** de los del rol hizo la operación.
- Un error (factura, abono) no es atribuible a persona dentro del mismo rol.
- Mitigación operativa sugerida: cuando ocurra un incidente, el cambio de clave del rol identifica el momento; la rotación anual obligatoria limita la ventana.

**Implementación técnica (entra en L3.6):**
- Los usuarios del mismo rol comparten el MISMO `password_hash`.
- Nueva función `change_role_password(rol, nueva_clave)` que actualiza el hash de TODOS los usuarios del rol (transaccional).
- `PASSWORD_EXPIRY_DAYS` = 365 (cambio anual).
- La UI de cambio de contraseña por rol se añade a la gestión de usuarios (solo ADMIN).

### Esquema objetivo de usuarios (definitivo — ROLES SOLO, sin nombres personales, decisión 23/09/2026)

| Cuenta | Rol | Clave | Estado |
|---|---|---|---|
| admin | ADMIN | Clave del rol ADMIN | Existe — rotar clave, forzar cambio |
| gerencia | GERENCIA | Clave del rol GERENCIA | Crear |
| operador | OPERADOR | Clave del rol OPERADOR | Crear |
| test_e2e / test_repro / test_repro2 | — | — | Desactivar |
| "Usuario 1" | legacy | — | Desactivar (no corresponde a rol definido) |

**Nota:** cuentas genéricas por rol (1 cuenta = 1 rol = 1 clave). Sin nombres de personas.

---

## 1. Mapa de Hallazgos → Lotes

| Lote | Hallazgos | Área | Riesgo |
|---|---|---|---|
| **L0** | S-1, S-2 (parte) | Datos de producción (cuentas) | 🔴 P0 |
| **L1** | E-1, E-6 (log), S-5, S-6, S-4 (log), E-5 (log) | Infraestructura de logging + arranque | 🔴 P0 |
| **L2** | E-2, E-3 | Sistema de backups | 🟠 P1 |
| **L3** | E-4, S-3, S-10, S-4 | Autenticación y sesión | 🟠 P1 |
| **L4** | E-6 (impresión) | tiquete_printer | 🟠 P1 |
| **L5** | Patrones sistémicos (19 print, ~25 except, 9+ DB handlers, ~30 .all(), 16 commits, 35 datetime) | Robustez transversal UI/servicios | 🟠 P1 |
| **L6** | S-2 (RBAC completo) | Control de acceso por roles | 🟠 P1 |
| **L7** | S-8, S-9, S-11 | Higiene de datos/config | 🟡 P2 |
| **L8** | E-0, S-7 | Migración de BD (proyecto) | 🔴 P1-proyecto |

**Eficiencia:** Los lotes L1-L4 y L7 son independientes entre sí → ejecutables en paralelo (máx. 2 agentes simultáneos para no pisarse en la BD de tests). L3 es prerequisito de L6. L5 es transversal y toca archivos de L1-L4 → se ejecuta después. L8 depende de L1 (necesita logs para validar migración) y de la decisión D1.

---

## 2. LOTE 0 — Remediación de datos de producción (P0, ~1-2 h)

**Precondición:** Backup manual de la BD + verificación de integridad ANTES de tocar datos. Autorización D5 = ✅ (mostrar SQL antes).

**Esquema objetivo de usuarios (definitivo — ROLES SOLO, ver sección 0):**

| Cuenta | Rol | Estado |
|---|---|---|
| admin | ADMIN | Existe — rotar clave, forzar cambio |
| gerencia | GERENCIA | Crear |
| operador | OPERADOR | Crear |
| test_e2e / test_repro / test_repro2 | — | Desactivar |
| "Usuario 1" | legacy | Desactivar |

| # | Tarea | Archivo/Destino | Verificación |
|---|---|---|---|
| L0.1 | **Forense previo**: consultar auditoría para ver actividad de las cuentas `test_e2e`, `test_repro`, `test_repro2` y `Usuario 1` (¿cuándo fue su último login? ¿crearon datos?) + verificar esquema de tabla `usuarios` (¿existe columna `activo`?) | BD (solo SELECT) | Reporte breve de hallazgos forenses + esquema conocido |
| L0.2 | **Backup pre-cambio**: `create_backup()` manual + `PRAGMA integrity_check` | backups/ | Backup con timestamp actual + "ok" |
| L0.3 | **Desactivar cuentas legacy/test**: `test_e2e`, `test_repro`, `test_repro2`, `Usuario 1` (via columna `activo` si existe, o eliminación física con verificación de FK). **Mostrar SQL al usuario antes de ejecutar (D5)** | BD producción | SELECT confirma desactivadas; login con esas cuentas falla |
| L0.4 | **Rotar contraseña del admin**: forzar cambio en próximo login (`requires_password_change=1` + `password_changed_at=NULL`) | BD producción | Admin ve pantalla de cambio obligatorio |
| L0.5 | **Crear cuentas por rol**: `gerencia` (rol GERENCIA) y `operador` (rol OPERADOR) con clave inicial aleatoria y `requires_password_change=1`. Claves entregadas al gerente (fuera de logs) | BD producción | SELECT muestra 3 cuentas (admin/gerencia/operador) con roles correctos; login con claves iniciales funciona |
| L0.6 | **Test de seguridad automatizado** (nuevo): test pytest que falle si existen cuentas `test_*` activas o usuarios sin rol | tests/test_seguridad_produccion.py | pytest verde con BD limpia de test_* |

**Nota:** L0.3-L0.5 modifican datos reales → ejecutar SOLO con autorización explícita (D5 = ✅) y SQL mostrado antes. Si no hay columna `activo` en `usuarios`, evaluar eliminación física con verificación de FK. Las claves iniciales de rol se generan aleatoriamente y se entregan al gerente para distribución (nunca en log).

---

## 3. LOTE 1 — Infraestructura de logging y arranque (P0, ~0.5-1 día)

**Objetivo:** Restaurar la observabilidad (E-1) y eliminar fugas de información en UI (S-6, S-4) y en log (S-5).

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L1.1 | **Crear `logging_setup.py`** (nuevo, ~40-60 líneas): RotatingFileHandler (5MB×5) a `%LOCALAPPDATA%\DELCA\logs\delca.log`; root INFO; `sys.excepthook` = log traceback + QMessageBox amable; redirect `sys.stdout`/`sys.stderr` a un tee del log; función `setup_logging()` | `src/core/logging_setup.py` (nuevo) | Nuevo archivo | Importa sin error; genera archivo de log al primer run |
| L1.2 | **Integrar en `main.py`**: primera línea del `main()` → `setup_logging()`; reemplazar `print()` de migraciones/datos maestros por `logger.error(..., exc_info=True)`; **migraciones fallidas → `raise` (abortar arranque)** en vez de print+continue; quitar `traceback.format_exc(limit=3)` del QMessageBox → mensaje genérico + referencia al log | `main.py` | Editar | Arranque limpio; log con "DELCA boot OK"; login fallido queda en log |
| L1.3 | **bootstrap_admin**: NO loguear la contraseña temporal; mostrarla en QMessageBox de primera ejecución; log genérico "Admin creado. Credencial entregada al operador." | `src/modules/usuarios/use_cases/bootstrap_admin.py` | Editar | Log sin password; UI muestra credencial 1 sola vez |
| L1.4 | **login_user**: error genérico "Error de autenticación. Intente nuevamente." en UI; `logger.error(..., exc_info=True)` con detalle | `src/modules/usuarios/use_cases/login_user.py` | Editar | Login con error interno no filtra internals |
| L1.5 | **usuarios_view**: verificar resultado real del commit ANTES de mostrar "Usuario reactivado"; log si falla | `src/modules/usuarios/views/usuarios_view.py` | Editar | Mensaje de éxito solo cuando commit OK |

**Verificación lote:** pytest completo (178+ tests) verde; lanzar app → `%LOCALAPPDATA%\DELCA\logs\delca.log` crece con eventos reales; `lsp_diagnostics` limpio.

---

## 4. LOTE 2 — Sistema de backups (P1, ~2-3 h)

**Objetivo:** Eliminar race condition (E-2) y crash en export (E-3).

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L2.1 | **Fix `export_to_csv`**: mover `conn.close()` después del bloque de headers vacíos; capturar headers ANTES de cerrar; o usar `conn` re-abierta | `src/core/services/backup_service.py` | Editar | Export de tabla vacía (ej. `facturas`) retorna OK sin crash |
| L2.2 | **Lock de backup**: implementar lock de archivo (`msvcrt.locking` en `.backup.lock` con retry/backoff) alrededor del check+create; o dedupe post-creación: si ya existe backup del mismo segundo/día, no duplicar | `src/core/services/backup_service.py` | Editar | 2 llamadas concurrentes → 1 solo backup |
| L2.3 | **Retención por día**: `_prune_old_backups` mantiene el PRIMERO del día (dedupe por `YYYYMMDD`) hasta 30 días, no 30 archivos | `src/core/services/backup_service.py` | Editar | 30 backups = 30 días de cobertura |
| L2.4 | **Backup async**: mover `create_backup()` a QThread (o `QTimer` + worker) para no congelar UI; deshabilitar botón durante ejecución | `src/core/views/backup_view.py`, `src/core/views/main_window.py` | Editar | UI responde durante backup de 8.5MB |
| L2.5 | **Backup con API SQLite**: evaluar `sqlite3.Connection.backup()` en vez de `shutil.copy2` (copia consistente sin depender del WAL checkpoint) | `src/core/services/backup_service.py` | Editar | Backup restaurable probado |

**Verificación lote:** `tests/test_backup_service.py` verde; prueba manual: 2 instancias → 1 backup; export tabla vacía OK; `lsp_diagnostics` limpio.

---

## 5. LOTE 3 — Autenticación y sesión (P1, ~1-2 h)

**Objetivo:** Timeouts correctos (E-4), auditoría de fuerza bruta (S-3), higiene de hash dummy (S-10).

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L3.1 | **Crear constantes de rol** (Enum `RolNombre` con ADMIN/GERENCIA/OPERADOR/CONSULTA) como única fuente de verdad | `src/modules/usuarios/models/rol_model.py` (o `src/core/constants.py` nuevo) | Nuevo/editar | Import sin error |
| L3.2 | **Fix `ROLE_TIMEOUTS`**: usar constantes del Enum; añadir entrada explícita para ADMIN y CONSULTA | `src/core/services/session_service.py` | Editar | Test: rol GERENCIA → 10800s; OPERADOR → None |
| L3.3 | **Auditar logins de usuarios inexistentes**: `registrar_login(usuario_id=NULL, exitoso=False, detalle=username)` antes del return | `src/modules/usuarios/use_cases/login_user.py` | Editar | FALLO_LOGIN aparece en auditoría para usernames inválidos |
| L3.4 | **Throttle global**: límite de intentos por username por ventana (ej. max 10/min) con sleep progresivo o bloqueo corto | `src/modules/usuarios/use_cases/login_user.py` | Editar | Test: 10+ intentos rápidos → 429-equivalente |
| L3.5 | **Documentar `DUMMY_BCRYPT_HASH`**: comentario explícito "hash defensivo, no credencial; rotación manual permitida" | `src/modules/usuarios/use_cases/login_user.py` | Editar | Comentario presente |
| L3.6 | **Política de contraseñas POR ROL** (decisión A3): implementar clave compartida por rol — los usuarios del mismo rol comparten el mismo `password_hash`; nueva función `change_role_password(rol, clave)` transaccional (actualiza todos los usuarios del rol); `PASSWORD_EXPIRY_DAYS` = 365; UI de cambio de clave por rol en gestión de usuarios (solo ADMIN) | `src/modules/usuarios/services/auth_service.py`, `src/modules/usuarios/services/usuario_service.py`, `src/modules/usuarios/views/usuarios_view.py`, `tests/test_auth_service.py` | Tests: cambiar clave del rol → todos los usuarios del rol inician sesión con la nueva; los de otros roles no. Expiración a 365 días |

**Verificación lote:** `tests/test_auth_service.py`, `tests/test_session_service.py` verdes; prueba manual de login con usuario inexistente → registro en auditoría + log.

---

## 6. LOTE 4 — Impresión de tiquetes (P1, ~30 min)

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L4.1 | **Fix lectura config**: try/except con log y advertencia UI (no defaults silenciosos) si el JSON de calibración está corrupto | `src/modules/llantas/services/tiquete_printer.py` | Editar | Config corrupta → aviso visible + log |
| L4.2 | **Fix escritura config**: envolver `CONFIG_PATH.write_text()` en try/except + log + feedback al usuario | `src/modules/llantas/services/tiquete_printer.py` | Editar | Guardado fallido → mensaje claro |

**Verificación lote:** prueba manual de guardar/cargar calibración; `lsp_diagnostics` limpio.

---

## 7. LOTE 5 — Robustez transversal (P1, ~1-2 días, paralelizable en subagentes)

**Objetivo:** Convertir los patrones frágiles en comportamiento observable y no-crash.

| # | Tarea | Alcance | Cambio | Verificación |
|---|---|---|---|---|
| L5.1 | **print() → logging**: reemplazar los 19 `print()` de vistas/servicios por `logger.info/error` (main_window, dashboard, clientes, usuarios, produccion, planta, productos, facturacion, cartera, kardex, inventario) | 11 archivos | Mecánico | grep confirma 0 prints de error restantes |
| L5.2 | **Handlers DB con try/except**: envolver las 9+ llamadas DB de handlers de botones en try/except con QMessageBox amigable + log (planta_view, produccion_view, llantas dialogs, facturacion pickers) | ~7 archivos | Editar | Fallo DB simulado → mensaje, no crash |
| L5.3 | **`.all()` con límite**: añadir `.limit()`/paginación donde la UI lo necesite en tablas grandes (llantas, clientes, facturas, productos, cartera, reportes) | ~20 sitios en services/repos | Editar | Queries devuelven N≤500; UI con paginación si aplica |
| L5.4 | **commits con manejo**: revisar los 16 `session.commit()` en flujos UI; usar `get_session()` context manager (ya hace rollback) o try/except explícito | ~6 archivos | Editar | No hay commit sin manejo en flujo UI |
| L5.5 | **datetime naive → aware** (parcial, el resto va en L8): documentar o estandarizar; mínimo: centralizar helper `now_local()` | `src/core/` nuevo helper | Editar | Tests datetime verdes |

**Verificación lote:** pytest completo verde; `lsp_diagnostics` limpio en los ~30 archivos tocados; smoke test de cada vista.

---

## 8. LOTE 6 — RBAC real (P1, semanas por periodo shadow)

**Estrategia expand-contract (validada por consultor):** constantes → middleware → shadow → cutover.

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L6.1 | **Middleware `require_permission(permiso)`** a nivel de servicio (no solo UI): decorator/helper central que consulta `permiso_service`; bypass explícito para ADMIN; rol desconocido → deny | `src/modules/usuarios/services/permiso_service.py` + helper nuevo | Nuevo/editar | Tests: matriz rol×permiso parametrizada |
| L6.2 | **Shadow mode**: flag `RBAC_ENFORCE=false` en config; loguear denials hipotéticos durante 1-2 semanas | `src/config.py`, middleware | Editar | Logs muestran denials sin bloquear operación |
| L6.3 | **Validar matriz de permisos**: contrastar los 27 permisos/68 asignaciones con la operación real (qué hace cada rol hoy) | Auditoría (read-only) | Análisis | Matriz corregida documentada |
| L6.4 | **Cutover por usuario**: activar enforcement usuario a usuario (primero el menos crítico), fuera de horario pico | Middleware + BD | Editar | Operación normal con roles activos |
| L6.5 | **Restringir restauración de backup a ADMIN** (`BACKUP_GESTIONAR`) + **auditar denials** | `backup_view.py`, auditoría | Editar | No-ADMIN no puede restaurar |

**Verificación lote:** shadow logs revisados; cutover completado sin tickets de soporte; tests RBAC verdes.

---

## 9. LOTE 7 — Higiene de datos/config (P2, ~2-3 h)

| # | Tarea | Archivo | Cambio | Verificación |
|---|---|---|---|---|
| L7.1 | **Parametrizar rutas de scripts**: 9 rutas `C:\Users\andre\...` → `argparse` o `.env` (migrar_materia_prima, migrar_marcas_dbf, importar_*csv, aplicar_precios) | 7 scripts | Editar | Scripts aceptan ruta por CLI |
| L7.2 | **ip/hostname en auditoría**: capturar `socket.gethostname()` o IP LAN en `registrar_login` y CRUD | `src/core/services/audit_service.py` | Editar | Auditoría nueva con hostname |
| L7.3 | **URL `delca.com`**: verificar/actualizar dominio real | `installer.iss` | Editar | Metadata correcta |
| L7.4 | **SECRET_KEY de la copia de trabajo** (divergencia): si `.omo/work/DELCA-ERP` se retoma, eliminar default inseguro | (copia de trabajo) | Editar | Sin default inseguro |

**Verificación lote:** scripts corren con ruta CLI; auditoría muestra hostname; `lsp_diagnostics` limpio.

---

## 10. LOTE 8 — Migración de BD (PROYECTO, 2-4 días + validación)

**Depende de:** D1, L1 (logs para validar), L5.5 (datetimes aware).

| # | Tarea | Cambio | Verificación |
|---|---|---|---|
| L8.1 | **Decisión D1** y aprovisionamiento del servidor (PG/SSE en PC del taller, servicio Windows, backup del servidor) | Infraestructura | Servidor responde; credenciales gestionadas |
| L8.2 | **Migración de datos**: script ETL SQLite→PG (tablas, tipos, AUTOINCREMENT→sequences, fechas a TIMESTAMPTZ, JSON) con conteo por tabla | Script nuevo | Conteos coinciden tabla a tabla (±0) |
| L8.3 | **Config app**: `DATABASE_URL` → PG; driver (psycopg); mantener `get_session()` | `src/config.py`, `src/database/engine.py` | Tests verdes contra PG (test CI) |
| L8.4 | **Normalizar datetimes** (35 naive → aware UTC) como parte del cambio de tipos | Modelos + servicios | Tests datetime verdes |
| L8.5 | **Backups del servidor**: pg_dump programado (diario) + **copias a OneDrive** (el patrón correcto: OneDrive sincroniza backups, no la BD viva) | Tarea programada Windows | Restauración probada de pg_dump |
| L8.6 | **Corte controlado**: día de corte; app en modo lectura durante migración; validación de 10-20 registros manuales; rollback planificado | Operación | Validación OK; rollback probado |
| L8.7 | **Retirar S-7**: BD fuera de OneDrive; permisos NTFS restringidos; cifrado en reposo evaluado (D6) | Infraestructura | Acceso solo autorizado |

**Verificación lote:** migración idéntica; app opera contra PG; restore drill OK; prueba de restauración trimestral documentada.

---

## 11. Secuencia y Estimación

```
Fase A (día 1):     L0 (datos)  →  1 h          [requiere D2, D3, D5]
Fase B (día 1-2):   L1 (logging) → 0.5-1 día     [desbloquea todo diagnóstico]
                    L2, L3, L4 en paralelo (máx 2 agentes)
Fase C (día 3-5):   L5 (robustez) + L7 (higiene) en paralelo
Fase D (sem 2-3):   L6 (RBAC shadow → cutover)   [requiere D2, D4]
Fase E (sem 2-6):   L8 (migración BD)            [requiere D1, D6]
```

**Total trabajo efectivo:** ~2 semanas · **Calendario con shadows/validación:** 4-6 semanas.

---

## 12. Definición de "Done" (criterios globales)

- [ ] Los 17 hallazgos tienen una tarea completada y verificada (traza Lote→Hallazgo).
- [ ] pytest completo verde (178 + nuevos tests de L0/L3/L6).
- [ ] `lsp_diagnostics` limpio en todos los archivos tocados.
- [ ] Logging funcional: `%LOCALAPPDATA%\DELCA\logs\delca.log` con eventos reales de producción.
- [ ] Cero cuentas `test_*` activas; todos los usuarios con rol distinto de ADMIN salvo 1 break-glass.
- [ ] Backup diario único (dedupe por día) con 30 días de cobertura.
- [ ] Migración de BD completada o interino acordado (D1).
- [ ] Prueba de restauración ejecutada y documentada.

---

## 13. Riesgos del plan

| Riesgo | Mitigación |
|---|---|
| Modificar datos de producción (L0) | Backup + integrity_check previo; SQL revisado; rollback SQL preparado |
| Migración BD rompe tipos/fechas | Conteos tabla a tabla; validación manual 10-20 registros; rollback planificado; app en modo lectura el día del corte |
| RBAC rompe operación diaria | Shadow mode 1-2 semanas; cutover por usuario; break-glass ADMIN |
| Cambios transversales (L5) introducen regresiones | pytest por lote; smoke test por vista; commits pequeños por archivo |
| Logging nuevo falla silenciosamente | Smoke test de arranque ("DELCA boot OK") como primer evento obligatorio |
| Dos copias de código divergentes | Trabajar SOLO sobre producción; sincronizar copia de trabajo al final o descartarla |

---

## 15. Estado de Ejecución (23/09/2026)

| Lote | Estado | Evidencia |
|---|---|---|
| **L0** — Cuentas | ✅ COMPLETO | 3 roles operativos (admin/gerencia/operador), 4 legacy/test bloqueadas, `scripts/verificar_seguridad.py` exit 0 |
| **L1** — Logging | ✅ COMPLETO | `src/core/logging_setup.py` → `%LOCALAPPDATA%\DELCA\logs\delca.log`; migraciones abortan en fallo; sin tracebacks en UI; contraseña fuera de logs; fix E-5 usuarios_view |
| **L2** — Backups | ✅ COMPLETO | Lock msvcrt + dedupe por día + retención 30 días; fix export tabla vacía (+bug headers cid→name); tests aislados de producción |
| **L3** — Auth | ✅ COMPLETO | `RolNombre` Enum; ROLE_TIMEOUTS corregido (GERENCIA=3h, OPERADOR=None); auditoría de usernames inexistentes; `sync_role_password` (clave por rol, verificada); expiración 365 días |
| **L4** — Impresión | ✅ COMPLETO | Config corrupta → log+aviso; guardado con manejo de errores |
| **L5.1** — print→logging | ✅ COMPLETO | 16/16 reemplazados en 11 vistas |
| **L5.2** — handlers DB | ✅ COMPLETO | Protegidos: planta_view, produccion_view, llantas _dialogs (×2), facturacion pickers (×2), form dialog |
| **L5.3** — `.all()` | ⚠️ EVALUADO | Paginación YA existe en viewmodel de llantas (PAGE_SIZE+offset). Los `.all()` restantes alimentan completers de selección completa — limitar rompería la búsqueda. Diferido con justificación |
| **L5.4** — commits | ✅ COMPLETO | usuarios_view (L1) + login_viewmodel rollback explícito; servicios usan `get_session()` con rollback automático |
| **L5.5** — datetime | ⚠️ DIFERIDO a L8 | El sistema es coherentemente naive hoy; normalizar es requisito de la migración PG (evita cambios a medias) |
| **L6** — RBAC | ✅ COMPLETO (infraestructura) | `require_permission()` + `RBAC_ENFORCE` (shadow mode) + aplicado a restauración de backup. Cutover real = semana de observación (operación, no código) |
| **L7.1** — rutas scripts | ✅ COMPLETO | 7/7 scripts → env vars `DELCA_ARCHIVO_*` (fallback conservado) + fix bug latente `import os` |
| **L7.2** — hostname auditoría | ✅ COMPLETO | `registrar_auditoria` captura hostname automáticamente |
| **L7.3** — delca.com | ✅ COMPLETO | Verificado: la empresa no tiene dominio web propio. `installer.iss` actualizado a su canal oficial público (LinkedIn verificado) con comentario documentando la decisión |
| **L8** — Migración PG | 🔧 SCRIPT LISTO | `scripts/migrar_a_postgresql.py` (ETL: esquema + datos + conteos, inspección verificada: 28 tablas). Ejecución bloqueada por infraestructura (requiere PC servidor + PostgreSQL) |

**Verificación global:** 180 tests passed · lsp limpio en archivos tocados · backup `delca_20260923_173734_369332.db` pre-cambio