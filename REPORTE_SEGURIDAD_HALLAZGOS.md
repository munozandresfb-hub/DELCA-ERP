# DELCA ERP — Reporte de Hallazgos de Seguridad

**Fecha:** 23 de septiembre de 2026
**Alcance:** Auditoría de seguridad del sistema DELCA ERP (Reencauchadora DELCA SAS) — aplicación de escritorio Windows, Python/PySide6/SQLite
**Objetivo:** Identificar vulnerabilidades, riesgos de exposición y malas prácticas de seguridad con severidad, evidencia y plan de remediación.

---

## 1. Resumen Ejecutivo

DELCA ERP es una aplicación **100% local** (SQLite embebido, sin backend remoto, sin librerías HTTP/red en `requirements.txt`), lo que reduce drásticamente su superficie de ataque. La auditoría confirma que el código hace las cosas bien en las áreas más críticas:

- ✅ **Inyección SQL: 0 vulnerabilidades** — toda la capa de aplicación usa SQLAlchemy ORM parametrizado; los scripts usan placeholders `?`; las migraciones interpolan solo constantes.
- ✅ **Secretos hardcodeados: 0 reales** — `.env` solo tiene placeholders, `.gitignore` excluye `delca.db` y `.env`, no hay credenciales de SMTP/API/correo.
- ✅ **Hashing de contraseñas correcto** — bcrypt con costo 12 (`$2b$12$`), verificado en los 5 usuarios de producción.
- ✅ **Mitigación de timing attack** en login, **lockout** de 5 intentos/15 min, **política de contraseñas** sólida, **expiración** a 90 días, **auditoría** de logins/CRUD.

Sin embargo, existen **2 hallazgos de severidad ALTA** que requieren acción inmediata porque son **cuentas de prueba con privilegios administrativos activas en producción** y **una configuración RBAC implementada pero completamente sin uso**:

| Severidad | Conteo | Hallazgos |
|---|---|---|
| **CRÍTICO** | 0 | — |
| **ALTO** | 2 | S-1: cuentas de prueba ADMIN en producción · S-2: RBAC sin uso real (todos los usuarios son ADMIN) |
| **MEDIO** | 5 | S-3: fuerza bruta de usernames sin límite ni auditoría · S-4: excepción cruda en error de login · S-5: contraseña temporal del admin en log · S-6: errores de arranque exponen rutas internas · S-7: BD sin cifrar con datos personales sincronizados por OneDrive |
| **BAJO** | 4 | S-8: ip_origen NULL · S-9: path disclosure · S-10: hash dummy documentable · S-11: URL placeholder |

---

## 2. Metodología

| Técnica | Alcance |
|---|---|
| Auditoría de inyección SQL | Todos los `execute()`, `text()`, f-strings SQL en `src/`, `scripts/`, `tests/` — ~60 hotspots en ~30 archivos |
| Búsqueda de secretos | Passwords, tokens, API keys, URLs con credenciales, certificados, SMTP, servicios externos en todo el proyecto |
| Auditoría de autenticación | `auth_service.py`, `login_user.py`, `bootstrap_admin.py`, `login_window.py`, `session_service.py` |
| Auditoría de RBAC | `bootstrap_rbac.py`, `permiso_service.py`, `main_window.py` (filtrado de vistas) |
| Inspección de BD de producción | Usuarios, roles, hashes, auditoría, migraciones (solo prefijos de hash, sin exponer valores) |
| Revisión de configuración | `.env`, `.env.example`, `.gitignore`, `build_exe.spec`, `installer.iss`, `requirements.txt` |

---

## 3. HALLAZGOS DE SEGURIDAD

### 🔴 S-1. Cuentas de prueba con rol ADMIN activas en producción (ALTO)

**Evidencia:** BD de producción, tabla `usuarios`:

| id | username | rol_id | last_login | requires_password_change |
|---|---|---|---|---|
| 1 | admin | 1 (ADMIN) | 2026-09-23 | 0 |
| 2 | Usuario 1 | 1 (ADMIN) | 2026-07-21 | 0 |
| 3 | **test_e2e** | **1 (ADMIN)** | 2026-07-21 | **1** |
| 4 | **test_repro** | **1 (ADMIN)** | 2026-08-28 | 0 |
| 5 | **test_repro2** | **1 (ADMIN)** | 2026-09-03 | 0 |

**Análisis:** Tres cuentas de prueba (`test_e2e`, `test_repro`, `test_repro2`) permanecen activas con privilegios de administrador total. `test_e2e` tiene `requires_password_change=1` y `password_changed_at=NULL` (nunca cambió su contraseña, que fue generada por un test E2E y es presumiblemente conocida). Estas cuentas son puertas traseras potenciales: cualquiera que conozca las contraseñas de prueba (visibles en el código de tests/historial) accede con rol ADMIN.

**Riesgo:** Alto. Compromiso total del sistema y de los datos (24.450 llantas, 5.241 clientes con NIT/teléfonos).

**Remediación:**
1. **Desactivar o eliminar** las 3 cuentas de prueba (SQL directo: `UPDATE usuarios SET activo=0 WHERE username LIKE 'test_%'` — o vía UI si existe el flag).
2. **Rotar la contraseña del admin** (`password_changed_at` data de 30/06/2026, expira el 28/09/2026).
3. **Crear usuarios individuales** para cada operador con contraseñas personales.
4. Añadir a `bootstrap_admin.py` o a la suite de tests una **verificación de que no existan cuentas `test_*`** en la BD de producción.

---

### 🔴 S-2. RBAC implementado pero sin uso real — todos los usuarios son ADMIN (ALTO)

**Evidencia:**
- Los **5 usuarios** de la BD tienen `rol_id=1` (ADMIN).
- El RBAC existe y funciona: 3 roles (`ADMIN`, `GERENCIA`, `OPERADOR`), 27 permisos, 68 asignaciones `roles_permisos`, y `main_window.py` filtra vistas por permiso.
- `bootstrap_admin.py` crea los roles estándar en cada arranque (idempotente).

**Análisis:** La infraestructura de seguridad de roles está construida pero **nadie la usa**. Cualquier usuario que loguee tiene acceso total a facturación, cartera, inventario, usuarios, backups y restauración. El riesgo operativo: un operador puede borrar/restaurar la BD, modificar precios, ver datos financieros sensibles.

**Riesgo:** Alto — no hay separación de privilegios efectiva. El modelo de "confianza total" es el más frágil en un negocio con datos financieros.

**Remediación (sin romper operación):**
1. **Asignar roles reales**: `Usuario 1` → `OPERADOR` (o `GERENCIA` si corresponde), crear usuarios para cada persona.
2. **Definir matriz de permisos por rol** (qué vistas/bloques puede ver cada rol) — ya existe la infraestructura.
3. **Verificar que el timeout de rol funcione** (ver hallazgo E-4 del reporte de estabilidad: claves de `ROLE_TIMEOUTS` no coinciden con los nombres de rol reales).
4. **Probar en staging** con 2-3 usuarios con roles distintos antes de aplicar en producción.
5. Restringir `BACKUP_GESTIONAR` (restauración) **solo a ADMIN** — restaurar una BD es una operación destructiva.

---

### 🟠 S-3. Fuerza bruta de usernames sin límite ni auditoría (MEDIO)

**Evidencia:** `login_user.py:42-53` — cuando el usuario NO existe:

```python
if not user:
    # Igualar el tiempo de respuesta (bcrypt dummy) para no revelar
    # si el usuario existe.
    AuthService.verify_password(password, DUMMY_BCRYPT_HASH)
    return { "success": False, ... }   # ← return SIN registrar auditoría
```

El comentario de las líneas 55-56 lo confirma: *"Audit: failed login for non-existent user"* está declarado pero **no implementado**. El `return` ocurre antes de cualquier `registrar_login(usuario_id=..., exitoso=False)`.

**Análisis:** La mitigación de timing attack (dummy bcrypt) iguala el tiempo de respuesta, lo que impide enumerar usuarios **por tiempo**. Pero:
- Los intentos contra usuarios inexistentes **no se auditan** (no aparecen como FALLO_LOGIN en la tabla `auditoria`).
- Los intentos contra usuarios inexistentes **no tienen límite de velocidad** (el lockout solo aplica a usuarios existentes).
- Un atacante local (empleado con acceso al equipo) puede probar miles de usernames por minuto sin dejar rastro.

**Riesgo:** Medio (la mitigación de tiempo existe, pero no hay registro ni límite).

**Remediación:**
1. Registrar auditoría para usuarios inexistentes (con `usuario_id=NULL` o `username` como detalle).
2. Añadir un **throttle global** por username probado (o por IP en el futuro).

---

### 🟠 S-4. Error de login expone excepción cruda al usuario (MEDIO)

**Evidencia:** `login_user.py:126-135`:

```python
except Exception as e:
    session.rollback()
    return {
        "success": False,
        ...
        "error": f"Error de autenticación: {e}",   # ← excepción cruda
    }
```

**Análisis:** Si ocurre un error interno (p. ej. un fallo de BD, un bug), el mensaje de error técnico se muestra en la UI del login. Esto puede filtrar rutas de archivos, nombres de tablas, versiones de librerías — información útil para un atacante.

**Riesgo:** Medio (bajo, porque es app local, pero es mala práctica y filtra internals).

**Remediación:**
1. Mostrar mensaje genérico: `"Error de autenticación. Intente nuevamente."`
2. Loguear la excepción completa: `logger.error("Error en login: %s", e, exc_info=True)`.

---

### 🟠 S-5. Contraseña temporal del admin escrita en el log (MEDIO)

**Evidencia:** `bootstrap_admin.py:50-53`:

```python
logging.getLogger("delca.startup").warning(
    "Admin creado con contraseña temporal: %s (cámbiela en el primer ingreso)",
    temp_password,
)
```

**Análisis:** La contraseña temporal (generada con `secrets.token_urlsafe(12)`) se registra en texto plano en `delca.log`. **Nota de coherencia con la auditoría de estabilidad:** hoy `delca.log` tiene 0 bytes (el logging está roto), por lo que es probable que esta contraseña **nunca llegara a escribirse** — el riesgo inmediato es bajo. PERO es una **bomba de tiempo**: en cuanto se arregle el logging (Fase 1 del plan de estabilidad), esta contraseña quedará escrita en disco cada vez que se cree un admin.

**Riesgo:** Medio. Cualquier persona con acceso al equipo/OneDrive puede leer la contraseña inicial del admin.

**Remediación:**
1. **NO loguear la contraseña**. Mostrarla solo en un `QMessageBox` en la primera ejecución (con aviso de "cambie esta contraseña") o entregarla por un canal seguro.
2. Si se loguea algo, que sea un identificador no secreto: `"Admin creado. Credencial inicial entregada al operador."`

---

### 🟠 S-6. Errores de arranque exponen rutas internas al usuario (MEDIO)

**Evidencia:** `main.py:156-164`:

```python
except Exception:
    logger.error("Error de arranque:\n%s", traceback.format_exc())
    ...
    QMessageBox.critical(None, "Error de arranque",
        "DELCA ERP no pudo iniciarse correctamente.\n\n"
        "Detalles:\n" + traceback.format_exc(limit=3))   # ← traceback en UI
```

**Análisis:** El usuario final ve el traceback con rutas absolutas del equipo (`C:\Users\andre\OneDrive\...`), nombres de módulos internos y potencialmente valores de variables.

**Riesgo:** Medio-bajo (fuga de información de entorno, no explotable directamente).

**Remediación:** Mostrar mensaje genérico en la UI y dejar el traceback completo solo en el log:
```python
QMessageBox.critical(None, "Error de arranque",
    "DELCA ERP no pudo iniciarse. Consulte el log en logs\\delca.log")
```

---

### 🟡 S-7. BD sin cifrar en reposo (BAJO — riesgo documentado)

**Evidencia:** `production_readiness_report.md:48` — *"BD encriptada: No (SQLite plano) 🟡"*.

**Análisis:** `delca.db` es un archivo SQLite plano con datos personales (NIT, cédulas, teléfonos, direcciones) y financieros (precios, saldos, cartera). Cualquier persona con acceso al equipo o a la copia de OneDrive puede abrirla con cualquier visor SQLite y leer TODO el contenido — incluyendo los hashes bcrypt (que son inútiles sin la contraseña, pero los datos son legibles).

**Agravante de arquitectura:** la BD vive en una **carpeta OneDrive sincronizada** (ver hallazgo E-0 del reporte de estabilidad). Esto significa que:
- Los datos personales/financieros de 5.241 clientes se **sincronizan a la nube de OneDrive** y a cada equipo que tenga la carpeta compartida (más superficie de exposición).
- Si el acceso a la carpeta OneDrive se comparte con cuentas ajenas al sistema (familia, otros dispositivos), los datos se exponen sin ningún control del ERP.
- Los 30 backups (≈270 MB) también viajan por la nube, multiplicando la superficie.

**Riesgo:** Medio (requiere acceso físico o a la cuenta OneDrive; no hay exfiltración remota posible desde la app).

**Remediación (evaluar):**
1. SQLCipher (SQLite cifrado) — requiere cambios en la cadena de conexión y manejo de clave.
2. Como mínimo: **asegurar que la BD y los backups no estén en una carpeta OneDrive pública/compartida** con otros dispositivos; restringir permisos NTFS a los usuarios del sistema. (La migración a PostgreSQL del plan de estabilidad resuelve esto de raíz: la BD vive en el servidor y solo los dumps van a OneDrive.)

---

### 🟡 S-8. `ip_origen` siempre NULL en auditoría (BAJO)

**Evidencia:** Los 1.071 registros de auditoría tienen `ip_origen = None`.

**Análisis:** En una app de escritorio local, la "IP de origen" no es muy relevante (todos son locales). Pero si se comparte en red (2-3 usuarios), saber **qué equipo** hizo cada operación sería útil forense. Hoy solo se registra `usuario_id`.

**Riesgo:** Bajo. **Remediación opcional:** capturar `socket.gethostname()` o la IP LAN al registrar.

---

### 🟡 S-9. Path disclosure en scripts de migración (BAJO)

**Evidencia:** 9 scripts contienen rutas absolutas del desarrollador: `scripts/migrar_materia_prima.py:41`, `migrar_marcas_dbf.py:21`, `importar_clientes_csv.py:35`, etc. — todas con `C:\Users\andre\OneDrive\Escritorio\DELCA\...`.

**Análisis:** No son credenciales, pero exponen el nombre de usuario Windows del desarrollador y la estructura de carpetas. Higiene: parametrizar con `argparse` o variables de entorno.

**Riesgo:** Bajo. **Remediación:** Mover rutas a argumentos de línea de comandos o `.env`.

---

### 🟡 S-10. Hash bcrypt dummy hardcodeado (BAJO — aceptable con documentación)

**Evidencia:** `login_user.py:14-16` — `DUMMY_BCRYPT_HASH = "$2b$12$2HBCUCt9/..."`.

**Análisis:** Es un hash bcrypt (unidireccional, no reversible) usado legítimamente para igualar tiempos de respuesta. No es un secreto filtrado. Sin embargo, un valor fijo hardcodeado es atípico y podría confundir a un auditor futuro.

**Riesgo:** Bajo. **Remediación:** Añadir comentario explícito ("hash dummy defensivo para mitigación de timing attack; no es una credencial").

---

### 🟡 S-11. URL placeholder `delca.com` en instalador (BAJO)

**Evidencia:** `installer.iss:12` — `#define MyAppURL "https://delca.com"`.

**Análisis:** Metadata del instalador Inno Setup. Si `delca.com` no es el dominio real de la empresa, queda información falsa en el instalador.

**Riesgo:** Bajo. **Remediación:** Verificar/actualizar el dominio real antes del release.

---

## 4. Búsquedas Negativas (no se encontraron)

| Categoría | Resultado |
|---|---|
| Inyección SQL explotable | ✅ 0 vulnerabilidades |
| Secretos/credenciales hardcodeados | ✅ 0 reales |
| Contraseñas en texto plano | ✅ 0 (bcrypt en todos los usuarios) |
| SMTP/credenciales de correo | ✅ No existen librerías ni config |
| APIs externas / pasarelas de pago | ✅ No existen integraciones |
| URLs con credenciales embebidas | ✅ 0 |
| Tokens JWT / API keys | ✅ 0 |
| Certificados/claves privadas | ✅ Solo CA bundle de pip en `.venv` |
| Librerías HTTP salientes | ✅ No en `requirements.txt` — la app no puede exfiltrar datos por red |
| NITs/teléfonos/emails reales en código | ✅ Solo fixtures sintéticos en tests |

---

## 5. Fortalezas Confirmadas (defensa en profundidad)

1. **ORM parametrizado en toda la capa de aplicación** — SQLAlchemy `.filter()`, `.ilike()`, placeholders `?` en scripts; migraciones con constantes internas; whitelist `ALL_TABLES` en exportaciones.
2. **Bcrypt costo 12** en todos los hashes de producción (verificado en los 5 usuarios).
3. **Bootstrap admin con contraseña aleatoria** (`secrets.token_urlsafe(12)`) + `requires_password_change=True` — nunca hardcodeada.
4. **Mitigación de timing attack** (dummy bcrypt) para usuarios inexistentes.
5. **Lockout de cuenta** (5 intentos / 15 min) + **expiración de contraseña** (90 días) + **política de complejidad** (mayúscula, minúscula, dígito, especial).
6. **Auditoría funcional**: 369 LOGIN, 123 FALLO_LOGIN, 375 LOGOUT, 203 CRUD events en 3 meses.
7. **`.gitignore` correcto**: `.env`, `delca.db`, `*.db`, `.venv`, `logs/`, `backups/` excluidos.
8. **Restauración de backup con verificación**: header SQLite + `PRAGMA integrity_check` + `.bak` de seguridad.
9. **Validación de CSV** con `csv.DictReader` + parametrización (aunque los importadores son admin-only).

---

## 6. Plan de Remediación Priorizado

### Fase 1 — Inmediata (esta semana): contener el acceso

| # | Acción | Severidad | Esfuerzo |
|---|---|---|---|
| 1.1 | **Desactivar/eliminar cuentas `test_e2e`, `test_repro`, `test_repro2`** en producción (antes: forense de su uso en la tabla de auditoría) | S-1 (ALTO) | 10 min |
| 1.2 | **Rotar contraseña del admin** (expira 28/09/2026 de todos modos) | S-1 (ALTO) | 10 min |
| 1.3 | **Asignar roles reales** a los usuarios existentes (OPERADOR/GERENCIA/ADMIN) y crear cuentas individuales | S-2 (ALTO) | 1-2 h |
| 1.4 | **Verificar permisos NTFS** de la carpeta DELCA y de `delca.db` (restringir a usuarios autorizados) + **revisar quién tiene acceso a la carpeta OneDrive** | S-7 (MEDIO) | 15 min |

### Fase 2 — Corto plazo (2-4 semanas): corregir código

| # | Acción | Severidad | Esfuerzo |
|---|---|---|---|
| 2.1 | **Auditar intentos de login de usuarios inexistentes** (`login_user.py`) + throttle global | S-3 (MEDIO) | 1 h |
| 2.2 | **Mensaje genérico en error de login** + log completo de la excepción | S-4 (MEDIO) | 15 min |
| 2.3 | **No loguear contraseña temporal del admin** (`bootstrap_admin.py`) — mostrar en UI de primera ejecución. **Importante: hacerlo ANTES de arreglar el logging** (hoy el log roto lo enmascara) | S-5 (MEDIO) | 30 min |
| 2.4 | **Quitar traceback de la UI** (`main.py`) — mensaje genérico + log | S-6 (MEDIO) | 15 min |
| 2.5 | **Fix ROLE_TIMEOUTS** (constantes de rol como única fuente de verdad) — sin esto el RBAC asignado en 1.3 no funciona | E-4 (estabilidad) | 30 min |
| 2.6 | **Restringir restauración de backup a ADMIN** (permiso `BACKUP_GESTIONAR` ya existe) | S-2 | 30 min |

### Fase 3 — Medio plazo (1-2 meses): endurecer

| # | Acción | Severidad | Esfuerzo |
|---|---|---|---|
| 3.1 | **Migrar la BD fuera de OneDrive** (PostgreSQL/SQL Server en PC servidor) — resuelve de raíz S-7 (datos fuera de la nube sincronizada) + E-0 (estabilidad) | S-7 + E-0 | Proyecto (2-4 días) |
| 3.2 | **RBAC con despliegue expand-contract**: constantes de rol → middleware `require_permission()` (bypass ADMIN) → shadow mode 1-2 semanas (loguear denials sin bloquear) → cutover por usuario → 1 ADMIN break-glass (dueño/gerente) | S-2 refuerzo | Medio (con periodo shadow) |
| 3.3 | **Capturar hostname/IP en auditoría** | S-8 | 1 h |
| 3.4 | **Parametrizar rutas de scripts** de migración | S-9 | 1 h |
| 3.5 | **Documentar `DUMMY_BCRYPT_HASH`** en código | S-10 | 5 min |
| 3.6 | **Verificar `delca.com`** en instalador | S-11 | 5 min |
| 3.7 | **Política de contraseñas**: evaluar subir mínimo a 10-12 caracteres; rotación cada 60-90 días; bloqueo prolongado tras N bloqueos | S-2 refuerzo | 2 h |
| 3.8 | **Test de seguridad automatizado**: verificar en CI que no existan cuentas `test_*` ni usuarios sin rol | S-1 refuerzo | 2 h |

---

## 7. Matriz de Riesgo Final

| # | Hallazgo | Severidad | Explotabilidad | Impacto | Prioridad |
|---|---|---|---|---|---|
| S-1 | Cuentas de prueba ADMIN en producción | **ALTO** | Alta (credenciales conocidas) | Total (datos + sistema) | **P0** |
| S-2 | RBAC sin uso — todos ADMIN | **ALTO** | Alta (cualquier empleado) | Total (datos + sistema) | **P0** |
| S-3 | Fuerza bruta de usernames sin límite/auditoría | MEDIO | Media (local) | Enumeración + abuso | P1 |
| S-4 | Excepción cruda en error de login | MEDIO | Baja | Fuga de internals | P1 |
| S-5 | Contraseña temporal en log | MEDIO | Media (acceso a log) | Compromiso cuenta admin | P1 |
| S-6 | Traceback en UI de arranque | MEDIO | Baja | Fuga de paths | P1 |
| S-7 | BD sin cifrar + datos en OneDrive compartido | **MEDIO** | Media (acceso a OneDrive/equipo) | Fuga de datos personales de 5.241 clientes | P1 |
| S-8 | Sin IP/host en auditoría | BAJO | — | Forense limitado | P2 |
| S-9 | Path disclosure en scripts | BAJO | Baja | Información de entorno | P2 |
| S-10 | Hash dummy documentable | BAJO | — | Confusión de auditoría | P2 |
| S-11 | URL placeholder | BAJO | — | Metadata falsa | P2 |

---

## 8. Veredicto

**El código de DELCA ERP está bien escrito desde la perspectiva de seguridad** (ORM parametrizado, bcrypt, lockout, auditoría, sin superficie de red). Los problemas graves no están en el código sino en la **gobernanza de producción**: cuentas de prueba con privilegios totales, un RBAC construido y desactivado, y datos personales sin cifrar en un archivo sincronizado por OneDrive.

**Prioridad de acción:**
1. **P0 (esta semana):** desactivar las 3 cuentas de prueba, rotar contraseña del admin, asignar roles reales. Bajo esfuerzo, alto impacto.
2. **P1 (2-4 semanas):** arreglar el login (auditoría de usernames inexistentes, mensajes genéricos), quitar la contraseña temporal del log **antes de arreglar el logging**, y el traceback de la UI.
3. **P1-P2 (1-2 meses):** migrar la BD fuera de OneDrive (resuelve de raíz la exposición de datos) y desplegar el RBAC real con estrategia expand-contract (constantes → shadow mode → cutover por usuario → 1 ADMIN break-glass).

La remediación P0 es de bajo esfuerzo y alto impacto, y debe hacerse antes de cualquier otra mejora funcional.