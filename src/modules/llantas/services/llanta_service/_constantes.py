ESTADOS_PROCESO = [
    "PENDIENTE",
    "APTA",
    "RECHAZADA",
    "REENCAUCHADA",
    "REPARADA",
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
# Definida según "Unificación de conceptos y flujos":
#   PENDIENTE → APTA | RECHAZADA            (veredicto inspección inicial)
#   APTA → REENCAUCHADA | REPARADA | RECHAZADA | APTA (reproceso en inspección final)
#   REENCAUCHADA/REPARADA/RECHAZADA → CLIENTE (retiro del cliente; el estado se conserva)
#   PENDIENTE → CLIENTE                      (retiro sin pasar por inspección)
TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "PENDIENTE": {"APTA", "RECHAZADA", "CLIENTE"},
    "APTA": {"REENCAUCHADA", "REPARADA", "RECHAZADA", "APTA"},
    "REENCAUCHADA": {"CLIENTE"},
    "REPARADA": {"CLIENTE"},
    "RECHAZADA": {"CLIENTE"},
}

# Estados que significan "en planta" (no entregada al cliente)
ESTADOS_EN_PLANTA = ("PENDIENTE", "APTA", "RECHAZADA", "REPARADA")