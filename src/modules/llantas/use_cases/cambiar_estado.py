from src.modules.llantas.services.llanta_service import LlantaService


def cambiar_estado(llanta_id, nuevo_estado):
    """Cambia el estado de una llanta validando la matriz de transiciones."""
    ok, msg = LlantaService.cambiar_estado(llanta_id, nuevo_estado)
    return ok