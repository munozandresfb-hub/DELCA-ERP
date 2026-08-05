# DELCA ERP — Piloto de 30 Días

**Versión:** 1.0.0
**Objetivo:** Validar ROI operativo y estabilidad del sistema antes de
producción multiusuario completa.

---

## Indicadores Clave de Éxito (KPI)

| KPI | Meta | Cómo se mide |
|---|---|---|
| Tiempo de actividad (uptime) | >99% | Logs de sesión (sin cierres inesperados) |
| Tiempo de respuesta de UI | <2s por operación | Percepción del usuario piloto |
| Backups completados | 30/30 días | `list_backups()` en backup_view |
| Errores de autenticación | <5/día en promedio | Tabla auditoría (FALLO_LOGIN) |
| Operaciones auditadas | 100% | Trazabilidad completa en tabla auditoria |
| Incidencias reportadas | <3 críticas | Registro del administrador |
| Usuarios activos simultáneos | 2-3 | Sesiones concurrentes |

---

## Semana 1 — Configuración y Pruebas Iniciales

### Día 1 — Instalación

- [ ] **Desplegar instalador** en equipo piloto
  - [ ] Ejecutar `DELCA_ERP_Setup_1.0.0.exe`
  - [ ] Verificar instalación en `C:\Program Files\DELCA ERP\`
  - [ ] Confirmar creación de `data/`, `backups/`, `logs/`
  - [ ] Verificar acceso directo en Escritorio
  - [ ] Verificar entrada en Menú Inicio

- [ ] **Configuración inicial**
  - [ ] Verificar `.env` con `DATABASE_URL=sqlite:///{app}\data\delca.db`
  - [ ] Iniciar la aplicación
  - [ ] Login con `admin / admin123`
  - [ ] **Cambiar contraseña de admin** (requerido en primer inicio)
  - [ ] Verificar que el dashboard carga correctamente

### Día 2 — Usuarios y Roles

- [ ] **Crear usuarios piloto**
  - [ ] Crear usuario GERENCIA: `gerente1`
  - [ ] Crear usuario OPERADOR: `operador1`
  - [ ] Crear usuario CONSULTA: `consulta1`
  - [ ] Asignar roles correctamente desde UI de Usuarios

- [ ] **Verificar RBAC**
  - [ ] Login como GERENCIA: debe ver Dashboard, Clientes, Llantas,
        Producción, Planta, Facturación, Cartera, Inventario, Kardex,
        Reportes, Automatización, Auditoría
  - [ ] Login como OPERADOR: debe ver todo excepto eliminar y anular
  - [ ] Login como CONSULTA: debe ver solo vistas, sin botones de acción
  - [ ] Login como ADMIN: debe ver el módulo Usuarios (los demás no)

### Día 3 — Operaciones Básicas

- [ ] **Flujo de Clientes**
  - [ ] Crear 5 clientes de prueba
  - [ ] Editar datos de un cliente
  - [ ] Buscar cliente por nombre y NIT
  - [ ] Verificar que la búsqueda funciona correctamente

- [ ] **Flujo de Llantas**
  - [ ] Registrar 10 llantas en inventario
  - [ ] Mover llantas entre ubicaciones
  - [ ] Cambiar estado de llanta

### Día 4 — Facturación y Cartera

- [ ] **Facturación**
  - [ ] Crear una factura de venta
  - [ ] Verificar numeración secuencial
  - [ ] Imprimir / visualizar factura

- [ ] **Cartera**
  - [ ] Registrar un pago contra una factura
  - [ ] Verificar saldo actualizado

### Día 5 — Backup y Recovery

- [ ] **Backup manual**
  - [ ] Navegar a módulo Backup
  - [ ] Ejecutar backup manual
  - [ ] Verificar archivo en `backups/delca_YYYYMMDD_HHMMSS.db`

- [ ] **Exportación de datos**
  - [ ] Exportar tabla clientes a CSV
  - [ ] Exportar tabla facturas a XLSX
  - [ ] Verificar que los archivos se abren correctamente

### Día 6-7 — Monitoreo

- [ ] **Verificar logs**
  - [ ] Revisar `logs/delca.log` — sin errores críticos
  - [ ] Revisar tabla `auditoria` — eventos de login/logout registrados

- [ ] **Prueba de recuperación**
  - [ ] Restaurar un backup desde la UI
  - [ ] Verificar integridad de datos post-restauración

---

## Semana 2 — Operación Controlada

### Día 8-10 — Carga de Datos Reales

- [ ] Migrar datos reales desde sistema anterior
  - [ ] Clientes activos
  - [ ] Inventario actual de llantas
  - [ ] Facturas pendientes
  - [ ] Saldos de cartera

- [ ] **Verificar consistencia**
  - [ ] Ejecutar `PRAGMA integrity_check` desde Backup UI
  - [ ] Verificar que los totales cuadran con sistema anterior

### Día 11-12 — Sesiones Concurrentes

- [ ] **Prueba multiusuario**
  - [ ] Sesión ADMIN abierta
  - [ ] Sesión OPERADOR abierta simultáneamente
  - [ ] Sesión CONSULTA abierta simultáneamente
  - [ ] Verificar que no hay conflictos de escritura

- [ ] **Timeout de sesión**
  - [ ] Dejar sesión inactiva 30 min
  - [ ] Verificar que la sesión expira y se cierra
  - [ ] Verificar evento LOGOUT en auditoría

### Día 13-14 — Reportes

- [ ] Generar reportes desde cada módulo
- [ ] Verificar que los datos son correctos
- [ ] Probar exportación de reportes

---

## Semana 3 — Validación de Seguridad

### Día 15-16 — Política de Contraseñas

- [ ] Probar bloqueo de cuenta (5 intentos fallidos)
- [ ] Verificar desbloqueo después de 15 min
- [ ] Verificar expiración de contraseña (cambiar fecha en BD para prueba)
- [ ] Verificar cambio forzado en primer login (nuevo usuario)

### Día 17-18 — Auditoría

- [ ] **Verificar trazabilidad**
  - [ ] Realizar un CREATE en clientes → buscar evento en auditoría
  - [ ] Realizar un UPDATE en llanta → buscar evento en auditoría
  - [ ] Consultar vista de auditoría (si existe en UI)

### Día 19-20 — Resiliencia

- [ ] **Prueba de integridad**
  - [ ] Forzar cierre de aplicación durante una operación
  - [ ] Reabrir y verificar consistencia de BD
  - [ ] Ejecutar integrity check

---

## Semana 4 — Cierre y Decisión

### Día 21-23 — Carga Máxima

- [ ] **Operación normal 3 días consecutivos**
  - [ ] Todos los días hábiles: facturar, cobrar, mover inventario
  - [ ] Backup automático diario verificado
  - [ ] Sin caídas del sistema

### Día 24-25 — Encuesta de Usuarios

- [ ] **Recolectar feedback de usuarios piloto:**
  - [ ] ¿La UI es intuitiva?
  - [ ] ¿Hay operaciones lentas?
  - [ ] ¿Falta alguna funcionalidad crítica?
  - [ ] ¿Los reportes tienen los datos correctos?
  - [ ] NPS (Net Promoter Score): __/10

### Día 26-27 — Revisión de Incidencias

- [ ] **Clasificar incidencias reportadas:**
  - [ ] Críticas (bloqueantes): ___ (meta: <3)
  - [ ] Mayores (afecta operación): ___
  - [ ] Menores (cosméticas): ___

### Día 28-30 — Decisión de Producción

- [ ] **Criterios de Go/No-Go:**
  - [ ] Score de producción readiness ≥ 90/100
  - [ ] < 3 incidencias críticas
  - [ ] Usuarios piloto aprueban (NPS ≥ 7)
  - [ ] Backups completados sin errores (todos los días hábiles)
  - [ ] Auditoría funcionando sin errores

- [ ] **Documentar resultados del piloto**
- [ ] **Decisión:** [ ] GO a producción | [ ] NO-GO, extender piloto

---

## Registro de Incidencias

| # | Fecha | Severidad | Descripción | Estado |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

---

## Aprobación Final

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Administrador del Sistema | | | |
| Usuario Piloto (Gerencia) | | | |
| Usuario Piloto (Operador) | | | |
| Sponsor del Proyecto | | | |
