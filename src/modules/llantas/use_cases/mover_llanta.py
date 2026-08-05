from src.modules.llantas.services.llanta_service import LlantaService


def mover_llanta(llanta_id, nueva_ubicacion):
    """Mueve una llanta a una nueva ubicación validando las ubicaciones permitidas."""
    ok, msg = LlantaService.mover_ubicacion(llanta_id, nueva_ubicacion)
    return ok