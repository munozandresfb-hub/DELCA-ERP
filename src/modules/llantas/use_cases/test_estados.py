from src.database.session import SessionLocal

from src.modules.clientes.models.cliente_model import Cliente
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.use_cases.cambiar_estado import cambiar_estado



def run_test():
    db = SessionLocal()

    # 1. Crear llanta demo
    llanta = Llanta(
        tiquete="DEL-TEST-002",
        marca="Michelin",
        dimension="295/80R22.5"
    )

    db.add(llanta)
    db.commit()
    db.refresh(llanta)

    llanta_id = llanta.id

    print("Llanta creada:", llanta.tiquete)

    # 2. Crear estado inicial
    estado_inicial = EstadoLlanta(
        llanta_id=llanta.id,
        estado="PENDIENTE"
    )

    db.add(estado_inicial)
    db.commit()
    db.close()

    print("Estado inicial registrado")

    # 3. Cambiar estados (flujo del documento)
    cambiar_estado(llanta_id, "APTA")
    cambiar_estado(llanta_id, "REENCAUCHADA")

    print("Historial de estados creado correctamente")


if __name__ == "__main__":
    run_test()