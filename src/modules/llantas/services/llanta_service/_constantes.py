ESTADOS_PROCESO = [
    "PENDIENTE",
    "APTA",
    "RECHAZADA",
    "REENCAUCHADA",
    "REPARADA",
    "REPROCESO",
]

# ── Ubicaciones de cadena productiva (futuras automatizaciones) ──
# Se conservan en código como referencia; operativamente la ubicación
# solo arroja PRODUCCION, no el paso específico de la cadena.
# CADENA_PRODUCTIVA = [
#     "INSPECCION_INICIAL",
#     "RASPADO",
#     "ESCAREO",
#     "REPARACION",
#     "CEMENTADO_RELLENO",
#     "EMBANDADO_CORTE",
#     "VULCANIZADO",
#     "INSPECCION_FINAL",
# ]

UBICACIONES_PLANTA = [
    "PRODUCCION",
    "PLANTA",
    "CLIENTE",
]

# Display names for locations map
UBICACIONES_DISPLAY: dict[str, str] = {
    "PRODUCCION": "Producción",
    "PLANTA": "Planta",
    "CLIENTE": "Cliente",
}

# ── Matriz de transiciones de estado válidas ──────────────────────
# Definida según "flujo correcto 2" (estados; la ubicación CLIENTE NO es un
# estado — se modela como cambio de ubicación vía COMBINACIONES_VALIDAS):
#   PENDIENTE → APTA | RECHAZADA              (veredicto inspección inicial)
#   APTA      → REENCAUCHADA | REPARADA | RECHAZADA | REPROCESO
#                                              (inspección final: 4 veredictos)
#   REPROCESO → REENCAUCHADA | REPARADA | RECHAZADA (inspección final repetida)
#   REENCAUCHADA/REPARADA/RECHAZADA → terminales (solo cambian de ubicación)
TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "PENDIENTE": {"APTA", "RECHAZADA"},
    "APTA": {"REENCAUCHADA", "REPARADA", "RECHAZADA", "REPROCESO"},
    "REPROCESO": {"REENCAUCHADA", "REPARADA", "RECHAZADA"},
    "REENCAUCHADA": set(),
    "REPARADA": set(),
    "RECHAZADA": set(),
}

# ── Veredictos de inspección final (opciones fijas en la UI) ──────
VEREDICTOS_INSPECCION_FINAL = (
    "REENCAUCHADA",
    "RECHAZADA",
    "REPARADA",
    "REPROCESO",
)

# ── Ubicaciones de cambio manual en Planta (opciones fijas en la UI) ──
# El cambio de ubicación manual en el módulo Planta ofrece siempre estas
# 2 opciones (Cliente, Planta). La validación final según el estado la
# hace el servicio (COMBINACIONES_VALIDAS).
UBICACIONES_CAMBIO_MANUAL = (
    "CLIENTE",
    "PLANTA",
)

# ── Veredicto de inspección → ubicación automática (flujo correcto 2) ──
# Regla R7: REPROCESO se mantiene en PRODUCCION.
VEREDICTO_UBICACION: dict[str, str] = {
    "APTA": "PRODUCCION",
    "REENCAUCHADA": "PLANTA",
    "REPARADA": "PLANTA",
    "RECHAZADA": "PLANTA",
    "REPROCESO": "PRODUCCION",
}

# ── Diseño de banda requerido para estado REPARADA (regla R5) ──
DISENO_REPARADA = "REP"

# ── Combinaciones válidas estado ↔ ubicación (reglas R1-R4, R6) ──
# R1: APTA no puede estar en CLIENTE.
# R2: PENDIENTE no puede estar en PRODUCCION.
# R3: REENCAUCHADA no puede estar en PRODUCCION.
# R4: REPARADA no puede estar en PRODUCCION.
# R6: CLIENTE solo admite REENCAUCHADA/REPARADA/RECHAZADA.
COMBINACIONES_VALIDAS: dict[str, set[str]] = {
    "PENDIENTE": {"PLANTA"},
    "APTA": {"PRODUCCION", "PLANTA"},
    "RECHAZADA": {"PLANTA", "CLIENTE"},
    "REENCAUCHADA": {"PLANTA", "CLIENTE"},
    "REPARADA": {"PLANTA", "CLIENTE"},
    "REPROCESO": {"PRODUCCION"},
}

# Estados que significan "en planta" (no entregada al cliente).
# Incluye REPROCESO (sigue en PRODUCCION, no entregada).
ESTADOS_EN_PLANTA = ("PENDIENTE", "APTA", "RECHAZADA", "REPARADA", "REENCAUCHADA", "REPROCESO")

# Estados que significan "en producción" (flujo correcto 2):
#   APTA: aceptada por inspección inicial → pasa a PRODUCCION.
#   REPROCESO: se mantiene en PRODUCCION mientras repite el proceso (R7).
ESTADOS_EN_PRODUCCION = ("APTA", "REPROCESO")

# Estados "terminadas" (producto terminado listo para entrega/venta).
ESTADOS_TERMINADAS = ("REENCAUCHADA", "REPARADA")