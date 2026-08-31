# 📋 Reporte de Auditoría — Flujo de Estados y Ubicaciones de Llantas

**Versión auditada**: Modelo "flujo correcto 2" (v2.5.0)
**Fecha**: 24/08/2026
**Estado del proyecto**: DELCA ERP — `Programacion DELCA v2`

---

## 1. Modelo conceptual vigente

### 1.1 Estados de llanta (6 válidos)

| Estado | Significado | Regla |
|---|---|---|
| `PENDIENTE` | Ingreso a sistema (registro inicial) | R2: no puede estar en PRODUCCION |
| `APTA` | Apta para reencauche (veredicto inspección inicial) | R1: no puede estar en CLIENTE |
| `RECHAZADA` | No apta para reencauche | — |
| `REENCAUCHADA` | Pasó inspección final | R3: no puede estar en PRODUCCION |
| `REPARADA` | Pasó inspección final (requiere diseño REP) | R4: no en PRODUCCION · R5: solo con REP |
| `REPROCESO` | Debe repetirse el proceso de reencauche | R7: se mantiene en PRODUCCION |

### 1.2 Ubicaciones de llanta (3 válidas)

| Ubicación | Display |
|---|---|
| `PRODUCCION` | Producción |
| `PLANTA` | Planta |
| `CLIENTE` | Cliente (entregada) |

> `CLIENTE` NO es un estado — es una **ubicación**. El estado se conserva al moverse a cliente (R6: solo Reencauchada, Reparada, Rechazada pueden estar en CLIENTE).

---

## 2. Matriz de transiciones (flujo correcto 2)

```python
TRANSICIONES_VALIDAS = {
    "PENDIENTE":     {"APTA", "RECHAZADA"},                    # veredicto inspección inicial
    "APTA":          {"REENCAUCHADA", "REPARADA", "REPROCESO"}, # inspección final
    "REPROCESO":     {"REENCAUCHADA", "REPARADA", "RECHAZADA"}, # inspección final repetida
    "REENCAUCHADA":  set(),   # terminal (solo cambia de ubicación)
    "REPARADA":      set(),   # terminal (solo cambia de ubicación)
    "RECHAZADA":     set(),   # terminal (solo cambia de ubicación)
}
```

### Veredicto → ubicación automática (VEREDICTO_UBICACION)

| Veredicto | Ubicación |
|---|---|
| APTA | PRODUCCION |
| REENCAUCHADA | PLANTA |
| REPARADA | PLANTA |
| RECHAZADA | PLANTA |
| REPROCESO | PRODUCCION (R7) |

### Combinaciones válidas (COMBINACIONES_VALIDAS — reglas R1-R4, R6)

| Estado | Ubicaciones permitidas |
|---|---|
| PENDIENTE | PLANTA |
| APTA | PRODUCCION, PLANTA |
| RECHAZADA | PLANTA, CLIENTE |
| REENCAUCHADA | PLANTA, CLIENTE |
| REPARADA | PLANTA, CLIENTE |
| REPROCESO | PRODUCCION |

---

## 3. El flujo real (cómo funciona hoy)

```
CREAR llanta
    │  estado = "PENDIENTE",  ubicacion_actual = "PLANTA" (historial inicial creado)
    ▼
PENDIENTE ──aplicar_veredicto(APTA)──► APTA ──aplicar_veredicto──► REENCAUCHADA / REPARADA
    │                                        │                          │
    └──aplicar_veredicto(RECHAZADA)──► RECHAZADA│                        │
                                                  └──► REPROCESO ──► REENCAUCHADA / REPARADA / RECHAZADA
                                                                              │
                                        mover_ubicacion(id, "CLIENTE") ◄───────┘
                                        (estado se conserva, solo cambia ubicación)
```

**Puntos de mutación:**

| Función | Cambia estado | Cambia ubicación | Validado |
|---|---|---|---|
| `crear()` | PENDIENTE | PLANTA (inicial) | ✅ |
| `cambiar_estado()` | ✅ (matriz) | ❌ no toca | ✅ |
| `mover_ubicacion()` | ❌ no toca | ✅ (COMBINACIONES_VALIDAS) | ✅ |
| `aplicar_veredicto()` | ✅ (matriz + R5) | ✅ (VEREDICTO_UBICACION) | ✅ atómico |

---

## 4. Hallazgos RESUELTOS (respecto a la auditoría anterior de 5 estados)

| Hallazgo previo | Estado | Solución |
|---|---|---|
| F1: `CLIENTE` como "estado" en la matriz (código muerto) | ✅ Resuelto | Matriz nueva sin CLIENTE; CLIENTE solo como ubicación |
| F2: `mover_ubicacion()` sin validar estado↔ubicación | ✅ Resuelto | `COMBINACIONES_VALIDAS` (R1-R4, R6) validado en servicio |
| F3: estado y ubicación divergen libremente | ✅ Resuelto | `aplicar_veredicto()` atómico + validación cruzada central |
| F4: bypass `LlantaRepository.update_estado()` | ✅ Resuelto | Método eliminado |
| F5: `aplicar_veredicto()` sin UI | ✅ Resuelto | Botón INSPECCIÓN FINAL en Producción |
| F6: sin constraints en BD para ubicaciones | ✅ Parcial | CHECK de 6 estados en llantas/estados_llanta (v2.5.0); ubicaciones siguen sin CHECK (decisión: validación en servicio) |
| F7: `crear()` sin ubicación inicial | ✅ Resuelto | `ubicacion_actual="PLANTA"` + historial inicial |
| F8: estados duplicados en 9 sitios | ✅ Resuelto | Centralizados en `_constantes.py` (ESTADOS_EN_PLANTA/PRODUCCION/TERMINADAS) |
| F9: `CambioRapidoDialog` muestra todos los estados | ✅ Resuelto | Diálogos filtran por transiciones/combinaciones válidas |
| F10: docs desactualizadas (8 estados legacy) | ✅ Resuelto | business_rules.md, Database_er.md, README.md, CHANGELOG.md |
| F11: indicador_reprocesadas() heurística | ✅ Según decisión | Se mantiene como reporte histórico aparte (no usa REPROCESO) |

---

## 5. Evidencia de verificación

| Verificación | Resultado |
|---|---|
| Suite de tests (`pytest`) | ✅ **132 passed, 0 failed** |
| Smoke test flujo completo (19 checks) | ✅ OK (Ingreso→Apta→Reproceso→Reencauchada→Cliente, R2/R3/R5/R6/R7) |
| Smoke test KPIs (8 checks) | ✅ OK (REPROCESO en producción, no en terminadas) |
| Migración v2.5.0 (dry-run + apply) | ✅ Constraints aplicados, datos corregidos, ids preservados |
| `run_migration()` idempotente | ✅ Detecta CHECK aplicado y salta |
| BD real | ✅ 8 llantas íntegras, 0 inconsistentes, 0 datos de prueba |
| Exe recompilado | ✅ 24/08/2026 17:06 (incluye todos los cambios) |

---

## 6. Recomendaciones pendientes

| Prioridad | Acción | Estado |
|---|---|---|
| P1 | Migración v2.5.0 registrada en `_migrations` | ✅ Hecho (run_migration + main.py) |
| P2 | Recompilar exe | ✅ Hecho |
| P3 | Backup automático + barra de estado | ✅ Hecho (Roadmap F1) |
| P4 | Cobertura de tests >70% (Roadmap F1) | ⏳ Pendiente |
| P5 | Scheduler backup: notificación al inicio | ✅ Hecho |
| P6 | CHECK constraint en BD para ubicaciones (defensa en profundidad) | ⏳ Opcional futuro |

---

**Veredicto**: el flujo correcto 2 está **implementado y activo** en el programa DELCA (código + BD + UI + tests + documentación). El modelo de 6 estados con matriz canónica centralizada elimina los riesgos de datos inconsistentes identificados en la auditoría previa.