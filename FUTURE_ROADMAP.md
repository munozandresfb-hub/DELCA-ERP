# DELCA ERP — Future Roadmap

**Versión:** 1.0.0
**Score actual:** 94/100
**Próximo hito:** v1.1 — Q3 2026

---

## Fase 1 — Madurez Operativa (Q3 2026) — Score objetivo: 97/100

### 1.1 Cobertura de Tests (>70%)
**Meta**: Alcanzar >70% de coverage en todos los módulos.

| Módulo | Prioridad | Acción |
|---|---|---|
| UI general | Alta | Tests con Playwright para flujos críticos (login, CRUD clientes, facturación) |
| Módulos de negocio | Alta | Tests unitarios para services y use cases de llantas, facturación, inventario |
| Backup UI | Media | Tests de integración para backup_view |
| CI/CD | Baja | Integrar pytest + pytest-cov en pipeline GitHub Actions |

### 1.2 Scheduler Automático de Backup
- Implementar `QTimer` en MainWindow que ejecute `create_backup()` diariamente
- Notificación visual al usuario del último backup
- Comprobación al inicio de la aplicación: si no hay backup hoy, recordatorio

### 1.3 Mejoras de UX
- Barra de estado con información del usuario, rol y último backup
- Notificaciones no intrusivas para expiración de contraseña (7 días antes)
- Confirmación adicional para operaciones destructivas (anular factura, eliminar)

---

## Fase 2 — Funcionalidades Avanzadas (Q4 2026) — Score objetivo: 98/100

### 2.1 Seguridad
| Feature | Prioridad | Descripción |
|---|---|---|
| Encriptación BD | Media | Migrar a SQLCipher para cifrado en reposo |
| 2FA | Baja | Autenticación de dos factores vía TOTP |
| Historial de sesiones | Baja | Mostrar sesiones activas y permitir cierre remoto |

### 2.2 Dashboard de Seguridad
- Usuarios activos vs bloqueados
- Contraseñas próximas a expirar
- Últimos inicios de sesión fallidos
- Resumen de actividad de auditoría

### 2.3 Exportación Avanzada
- Reportes programados (PDF programado semanal/mensual)
- Envío por email automatizado
- Dashboard de indicadores clave (KPI)

---

## Fase 3 — Escalabilidad (Q1 2027) — Score objetivo: 99/100

### 3.1 Migración a PostgreSQL
- Migración completa de SQLite a PostgreSQL
- Script de migración de datos (`pg_dump` / `SQLAlchemy`)
- Configuración de respaldo en caliente (PgBouncer + streaming replication)
- Actualizar `installer.iss` para incluir PostgreSQL opcional

### 3.2 Multi-Sucursal
- Modelo de sucursales con inventario separado
- Facturación por sucursal
- Reportes consolidados multi-sucursal

### 3.3 API REST
- API RESTful con FastAPI para integración con sistemas externos
- Autenticación vía JWT
- Documentación OpenAPI/Swagger

---

## Fase 4 — Innovación (Q2 2027+) — Score objetivo: 100/100

### 4.1 Mobile-First
- App React Native para consulta de indicadores
- Notificaciones push (alertas de inventario bajo, facturas vencidas)
- Escaneo de códigos de barras para entrada/salida de inventario

### 4.2 Automatización Inteligente
- Reglas de negocio configurables desde UI (actualmente en código)
- Alertas automáticas por email/SMS
- Integración con proveedores (API de pedidos automatizados)

### 4.3 Business Intelligence
- Dashboard ejecutivo con gráficos interactivos
- Análisis de tendencias (ventas, rotación de inventario)
- Exportación automática de reportes periódicos

---

## Resumen de Roadmap

| Fase | Período | Score Objetivo | Inversión Estimada |
|---|---|---|---|
| F1: Madurez Operativa | Q3 2026 | 97/100 | 40h |
| F2: Funcionalidades Avanzadas | Q4 2026 | 98/100 | 80h |
| F3: Escalabilidad | Q1 2027 | 99/100 | 120h |
| F4: Innovación | Q2 2027+ | 100/100 | 200h+ |

---

## Mantenimiento Continuo

| Actividad | Frecuencia | Responsable |
|---|---|---|
| Backup de BD | Diario (automático) | Sistema |
| Verificación de integridad BD | Semanal | Administrador |
| Revisión de logs de auditoría | Mensual | Administrador |
| Actualización de contraseñas | Cada 90 días | Usuarios |
| Pruning de backups antiguos | Automático (>30) | Sistema |
| Revisión de permisos de usuario | Trimestral | Administrador |
