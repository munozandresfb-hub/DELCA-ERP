from src.database.session import SessionLocal

from src.modules.clientes.models.cliente_model import Cliente
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.use_cases.mover_llanta import mover_llanta


def run_test():
    db = SessionLocal()

    # Crear llanta demo con tiquete nuevo (IMPORTANTE)
    llanta = Llanta(
        tiquete="DEL-UBI-001",
        marca="Bridgestone",
        dimension="315/80R22.5"
    )

    db.add(llanta)
    db.commit()
    db.refresh(llanta)

    llanta_id = llanta.id

    print("Llanta creada:", llanta.tiquete)

    # Ubicación inicial
    ubicacion_inicial = UbicacionLlanta(
        llanta_id=llanta.id,
        ubicacion="PRODUCCION"
    )

    db.add(ubicacion_inicial)
    db.commit()
    db.close()

    print("Ubicación inicial registrada")

    # Mover llanta por planta
    mover_llanta(llanta_id, "RASPADO")
    mover_llanta(llanta_id, "REPARACION")
    mover_llanta(llanta_id, "VULCANIZADO")

    print("Historial de ubicaciones creado correctamente")


if __name__ == "__main__":
    run_test()