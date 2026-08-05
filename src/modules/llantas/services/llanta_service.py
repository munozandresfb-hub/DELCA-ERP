from src.database.engine import get_session
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository


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


class LlantaService:
    """Business logic for tire management."""

    @staticmethod
    def listar_llantas() -> list[Llanta]:
        with get_session() as session:
            llantas = LlantaRepository.get_all(session)
            for ll in llantas:
                session.expunge(ll)
            return llantas

    @staticmethod
    def buscar(
        term: str = "",
        estado: str | None = None,
        cliente_id: int | None = None,
    ) -> list[Llanta]:
        with get_session() as session:
            llantas = LlantaRepository.search(
                session, term=term, estado=estado, cliente_id=cliente_id
            )
            for ll in llantas:
                session.expunge(ll)
            return llantas

    @staticmethod
    def obtener_por_id(llanta_id: int) -> Llanta | None:
        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if llanta:
                session.expunge(llanta)
            return llanta

    @staticmethod
    def tiquete_existe(tiquete: str) -> bool:
        """Return True if a tire with the given tiquete already exists.

        Used for live validation in the UI (before the user hits Guardar).
        """
        if not tiquete or not tiquete.strip():
            return False
        with get_session() as session:
            return (
                LlantaRepository.get_by_tiquete(session, tiquete.strip()) is not None
            )

    @staticmethod
    def crear(
        tiquete: str,
        marca_id: int | None = None,
        dimension_id: int | None = None,
        diseno_id: int | None = None,
        ancho: int | None = None,
        perfil: int | None = None,
        rin: int | None = None,
        indice_carga: str | None = None,
        velocidad: str | None = None,
        capas: str | None = None,
        peso_maximo: float | None = None,
        posicion: str | None = None,
        rendimiento_km: int | None = None,
        costo_produccion: float | None = None,
        precio_venta: float | None = None,
        asesor: str | None = None,
        cliente_id: int | None = None,
        # ── Orden de Servicio ───────────────────────────────────────────
        numero_orden: str | None = None,
        consecutivo: str | None = None,
        dot: str | None = None,
        observaciones: str | None = None,
        fecha_ingreso = None,
    ) -> tuple[bool, str | Llanta]:
        if not tiquete or not tiquete.strip():
            return False, "El tiquete es obligatorio"

        with get_session() as session:
            existente = LlantaRepository.get_by_tiquete(session, tiquete.strip())
            if existente:
                return False, f"Ya existe una llanta con tiquete {tiquete}"

            # Resolve catalog names for legacy text fields
            marca_text = None
            dimension_text = None
            if marca_id:
                marcas = LlantaRepository.get_all_marcas(session)
                marca_obj = next((m for m in marcas if m.id == marca_id), None)
                marca_text = marca_obj.nombre if marca_obj else None
            if dimension_id:
                dimensiones = LlantaRepository.get_all_dimensiones(session)
                dimension_obj = next(
                    (d for d in dimensiones if d.id == dimension_id), None
                )
                dimension_text = dimension_obj.display if dimension_obj else None

            llanta = Llanta(
                tiquete=tiquete.strip(),
                marca=marca_text,
                dimension=dimension_text,
                marca_id=marca_id,
                dimension_id=dimension_id,
                diseno_id=diseno_id,
                ancho=ancho,
                perfil=perfil,
                rin=rin,
                indice_carga=indice_carga,
                velocidad=velocidad,
                capas=capas,
                peso_maximo=peso_maximo,
                posicion=posicion,
                rendimiento_km=rendimiento_km,
                costo_produccion=costo_produccion,
                precio_venta=precio_venta,
                asesor=asesor,
                estado="PENDIENTE",
                cliente_id=cliente_id,
                numero_orden=numero_orden,
                consecutivo=consecutivo,
                dot=dot,
                observaciones=observaciones,
                fecha_ingreso=fecha_ingreso,
            )
            llanta = LlantaRepository.create(session, llanta)

            # Create initial estado
            historial = EstadoLlanta(llanta_id=llanta.id, estado="PENDIENTE")
            session.add(historial)

            session.expunge(llanta)
            return True, llanta

    @staticmethod
    def cambiar_estado(
        llanta_id: int, nuevo_estado: str
    ) -> tuple[bool, str]:
        if nuevo_estado not in ESTADOS_PROCESO:
            return False, f"Estado inválido: {nuevo_estado}"

        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if not llanta:
                return False, "Llanta no encontrada"

            # Validar transición según la matriz del flujo
            estado_actual = llanta.estado or "PENDIENTE"
            permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
            if nuevo_estado not in permitidos:
                return False, (
                    f"Transición inválida: '{estado_actual}' no puede pasar "
                    f"directamente a '{nuevo_estado}'"
                )

            llanta.estado = nuevo_estado
            historial = EstadoLlanta(
                llanta_id=llanta_id, estado=nuevo_estado
            )
            session.add(historial)
            return True, f"Estado cambiado a '{nuevo_estado}'"

    @staticmethod
    def mover_ubicacion(
        llanta_id: int, ubicacion: str
    ) -> tuple[bool, str]:
        if ubicacion not in UBICACIONES_PLANTA:
            return False, f"Ubicación inválida: {ubicacion}"

        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if not llanta:
                return False, "Llanta no encontrada"

            movimiento = UbicacionLlanta(
                llanta_id=llanta_id, ubicacion=ubicacion
            )
            session.add(movimiento)
            llanta.ubicacion_actual = ubicacion
            return True, f"Llanta movida a '{ubicacion}'"

    @staticmethod
    def aplicar_veredicto(
        llanta_id: int, veredicto: str
    ) -> tuple[bool, str]:
        """Aplica un veredicto de inspección: cambia estado y ubicación
        de forma atómica según el flujo definido en "Unificación de
        conceptos y flujos".

        Veredictos válidos:
          - APTA         → estado APTA, ubicación PRODUCCION
          - REENCAUCHADA → estado REENCAUCHADA, ubicación PLANTA
          - REPARADA     → estado REPARADA, ubicación PLANTA
          - RECHAZADA    → estado RECHAZADA, ubicación PLANTA
        """
        VEREDICTO_UBICACION = {
            "APTA": "PRODUCCION",
            "REENCAUCHADA": "PLANTA",
            "REPARADA": "PLANTA",
            "RECHAZADA": "PLANTA",
        }
        if veredicto not in VEREDICTO_UBICACION:
            return False, (
                f"Veredicto inválido: {veredicto}. "
                f"Válidos: {', '.join(VEREDICTO_UBICACION)}"
            )

        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if not llanta:
                return False, "Llanta no encontrada"

            # Validar transición según la matriz del flujo
            estado_actual = llanta.estado or "PENDIENTE"
            permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
            if veredicto not in permitidos:
                return False, (
                    f"Transición inválida: '{estado_actual}' no puede pasar "
                    f"directamente a '{veredicto}'"
                )

            # Estado + ubicación en la misma transacción
            llanta.estado = veredicto
            llanta.ubicacion_actual = VEREDICTO_UBICACION[veredicto]

            session.add(
                EstadoLlanta(llanta_id=llanta_id, estado=veredicto)
            )
            session.add(
                UbicacionLlanta(
                    llanta_id=llanta_id,
                    ubicacion=VEREDICTO_UBICACION[veredicto],
                )
            )
            return True, (
                f"Veredicto '{veredicto}' aplicado — "
                f"ubicación: {VEREDICTO_UBICACION[veredicto]}"
            )

    @staticmethod
    def obtener_historial_estados(
        llanta_id: int,
    ) -> list[EstadoLlanta]:
        with get_session() as session:
            return (
                session.query(EstadoLlanta)
                .filter(EstadoLlanta.llanta_id == llanta_id)
                .order_by(EstadoLlanta.fecha.desc())
                .all()
            )

    @staticmethod
    def obtener_historial_ubicaciones(
        llanta_id: int,
    ) -> list[UbicacionLlanta]:
        with get_session() as session:
            return (
                session.query(UbicacionLlanta)
                .filter(UbicacionLlanta.llanta_id == llanta_id)
                .order_by(UbicacionLlanta.fecha.desc())
                .all()
            )

    @staticmethod
    def contar_por_estado() -> dict[str, int]:
        with get_session() as session:
            return LlantaRepository.count_by_estado(session)

    # ── Catalog helpers ───────────────────────────────────────────────

    @staticmethod
    def listar_marcas() -> list:
        with get_session() as session:
            return LlantaRepository.get_all_marcas(session)

    @staticmethod
    def listar_dimensiones() -> list:
        with get_session() as session:
            return LlantaRepository.get_all_dimensiones(session)

    @staticmethod
    def listar_disenos() -> list:
        from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta
        with get_session() as session:
            return session.query(DisenoLlanta).order_by(DisenoLlanta.nombre).all()

    # ── CRUD Marcas ─────────────────────────────────────────────────

    @staticmethod
    def crear_marca(nombre: str, siglas: str = "") -> tuple[bool, str]:
        if not nombre or not nombre.strip():
            return False, "El nombre de la marca es obligatorio"
        from src.modules.llantas.models.marca_llanta_model import MarcaLlanta
        with get_session() as session:
            existe = session.query(MarcaLlanta).filter(
                MarcaLlanta.nombre == nombre.strip()
            ).first()
            if existe:
                return False, f"La marca '{nombre}' ya existe"
            s = siglas.strip().upper() if siglas else None
            session.add(MarcaLlanta(nombre=nombre.strip(), siglas=s))
            return True, f"Marca '{nombre}' creada"

    @staticmethod
    def actualizar_marca(marca_id: int, nombre: str, siglas: str = "") -> tuple[bool, str]:
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        from src.modules.llantas.models.marca_llanta_model import MarcaLlanta
        with get_session() as session:
            marca = session.query(MarcaLlanta).filter(MarcaLlanta.id == marca_id).first()
            if not marca:
                return False, "Marca no encontrada"
            duplicado = session.query(MarcaLlanta).filter(
                MarcaLlanta.nombre == nombre.strip(),
                MarcaLlanta.id != marca_id,
            ).first()
            if duplicado:
                return False, f"Ya existe otra marca con el nombre '{nombre}'"
            marca.nombre = nombre.strip()
            marca.siglas = siglas.strip().upper() if siglas else None
            return True, "Marca actualizada"

    @staticmethod
    def eliminar_marca(marca_id: int) -> tuple[bool, str]:
        from src.modules.llantas.models.marca_llanta_model import MarcaLlanta
        with get_session() as session:
            marca = session.query(MarcaLlanta).filter(MarcaLlanta.id == marca_id).first()
            if not marca:
                return False, "Marca no encontrada"
            llantas_rel = session.query(Llanta).filter(Llanta.marca_id == marca_id).count()
            if llantas_rel > 0:
                return False, f"No se puede eliminar: {llantas_rel} llanta(s) usan esta marca"
            session.delete(marca)
            return True, "Marca eliminada"

    # ── CRUD Dimensiones ─────────────────────────────────────────────

    @staticmethod
    def crear_dimension(ancho: int, perfil: int | None, rin: int | float | None) -> tuple[bool, str]:
        if ancho <= 0 or (perfil is not None and perfil <= 0) or (isinstance(rin, (int, float)) and rin <= 0):
            return False, "Ancho y rin deben ser positivos; perfil (si se indica) debe ser mayor que 0"
        from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta
        display = DimensionLlanta(ancho=ancho, perfil=perfil, rin=rin).display  # noqa
        with get_session() as session:
            existe = session.query(DimensionLlanta).filter(
                DimensionLlanta.ancho == ancho,
                DimensionLlanta.perfil == perfil,
                DimensionLlanta.rin == rin,
            ).first()
            if existe:
                return False, f"La dimensión {display} ya existe"
            session.add(DimensionLlanta(ancho=ancho, perfil=perfil, rin=rin))
            return True, f"Dimensión {display} creada"

    @staticmethod
    def actualizar_dimension(dimension_id: int, ancho: int, perfil: int | None, rin: int | float | None) -> tuple[bool, str]:
        if ancho <= 0 or (perfil is not None and perfil <= 0) or (isinstance(rin, (int, float)) and rin <= 0):
            return False, "Ancho y rin deben ser positivos; perfil (si se indica) debe ser mayor que 0"
        from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta
        display = DimensionLlanta(ancho=ancho, perfil=perfil, rin=rin).display  # noqa
        with get_session() as session:
            dimension = session.query(DimensionLlanta).filter(DimensionLlanta.id == dimension_id).first()
            if not dimension:
                return False, "Dimensión no encontrada"
            duplicado = session.query(DimensionLlanta).filter(
                DimensionLlanta.ancho == ancho,
                DimensionLlanta.perfil == perfil,
                DimensionLlanta.rin == rin,
                DimensionLlanta.id != dimension_id,
            ).first()
            if duplicado:
                return False, f"La dimensión {display} ya existe"
            dimension.ancho = ancho
            dimension.perfil = perfil
            dimension.rin = rin
            return True, "Dimensión actualizada"

    @staticmethod
    def eliminar_dimension(dimension_id: int) -> tuple[bool, str]:
        from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta
        from src.modules.inventario.models.precio_producto_model import PrecioProducto
        from src.modules.inventario.models.inventario_config_models import (
            CostoProduccionEstandar, RecetaProduccion, PrecioVentaCliente,
        )
        with get_session() as session:
            dimension = session.query(DimensionLlanta).filter(DimensionLlanta.id == dimension_id).first()
            if not dimension:
                return False, "Dimensión no encontrada"
            deps = 0
            deps += session.query(PrecioProducto).filter(PrecioProducto.dimension_id == dimension_id).count()
            deps += session.query(CostoProduccionEstandar).filter(CostoProduccionEstandar.dimension_id == dimension_id).count()
            deps += session.query(RecetaProduccion).filter(RecetaProduccion.dimension_id == dimension_id).count()
            deps += session.query(PrecioVentaCliente).filter(PrecioVentaCliente.dimension_id == dimension_id).count()
            if deps > 0:
                return False, f"No se puede eliminar: {deps} registro(s) usan esta dimensión"
            session.delete(dimension)
            return True, "Dimensión eliminada"

    # ── CRUD Diseños ────────────────────────────────────────────────

    @staticmethod
    def crear_diseno(nombre: str, tipo: str) -> tuple[bool, str]:
        if not nombre or not nombre.strip():
            return False, "El nombre del diseño es obligatorio"
        tipo = (tipo or "").strip().upper()
        from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta, TIPOS_DISENO
        if tipo not in TIPOS_DISENO:
            return False, f"Tipo inválido: debe ser {', '.join(TIPOS_DISENO)}"
        with get_session() as session:
            existe = session.query(DisenoLlanta).filter(
                DisenoLlanta.nombre == nombre.strip(),
            ).first()
            if existe:
                return False, f"El diseño '{nombre}' ya existe"
            session.add(DisenoLlanta(nombre=nombre.strip(), tipo=tipo))
            return True, f"Diseño '{nombre}' ({tipo}) creado"

    @staticmethod
    def actualizar_diseno(diseno_id: int, nombre: str, tipo: str) -> tuple[bool, str]:
        if not nombre or not nombre.strip():
            return False, "El nombre del diseño es obligatorio"
        tipo = (tipo or "").strip().upper()
        from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta, TIPOS_DISENO
        if tipo not in TIPOS_DISENO:
            return False, f"Tipo inválido: debe ser {', '.join(TIPOS_DISENO)}"
        with get_session() as session:
            diseno = session.query(DisenoLlanta).filter(DisenoLlanta.id == diseno_id).first()
            if not diseno:
                return False, "Diseño no encontrado"
            duplicado = session.query(DisenoLlanta).filter(
                DisenoLlanta.nombre == nombre.strip(),
                DisenoLlanta.id != diseno_id,
            ).first()
            if duplicado:
                return False, f"Ya existe otro diseño con el nombre '{nombre}'"
            diseno.nombre = nombre.strip()
            diseno.tipo = tipo
            return True, "Diseño actualizado"

    @staticmethod
    def eliminar_diseno(diseno_id: int) -> tuple[bool, str]:
        from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta
        from src.modules.llantas.models.llanta_model import Llanta
        from src.modules.inventario.models.precio_producto_model import PrecioProducto
        from src.modules.inventario.models.inventario_config_models import (
            CostoProduccionEstandar, RecetaProduccion, PrecioVentaCliente,
        )
        with get_session() as session:
            diseno = session.query(DisenoLlanta).filter(DisenoLlanta.id == diseno_id).first()
            if not diseno:
                return False, "Diseño no encontrado"
            deps = 0
            deps += session.query(Llanta).filter(Llanta.diseno_id == diseno_id).count()
            deps += session.query(PrecioProducto).filter(PrecioProducto.diseno_id == diseno_id).count()
            deps += session.query(CostoProduccionEstandar).filter(CostoProduccionEstandar.diseno_id == diseno_id).count()
            deps += session.query(RecetaProduccion).filter(RecetaProduccion.diseno_id == diseno_id).count()
            deps += session.query(PrecioVentaCliente).filter(PrecioVentaCliente.diseno_id == diseno_id).count()
            if deps > 0:
                return False, f"No se puede eliminar: {deps} registro(s) usan este diseño"
            session.delete(diseno)
            return True, "Diseño eliminado"

    # ── CRUD Causas de Rechazo ──────────────────────────────────────

    @staticmethod
    def listar_causas_rechazo() -> list:
        from src.modules.llantas.models.causa_rechazo_model import CausaRechazo
        with get_session() as session:
            return session.query(CausaRechazo).order_by(CausaRechazo.codigo).all()

    @staticmethod
    def crear_causa_rechazo(codigo: str, descripcion: str, categoria: str = "") -> tuple[bool, str]:
        if not codigo or not codigo.strip():
            return False, "El código es obligatorio"
        if not descripcion or not descripcion.strip():
            return False, "La descripción es obligatoria"
        from src.modules.llantas.models.causa_rechazo_model import CausaRechazo
        with get_session() as session:
            existe = session.query(CausaRechazo).filter(
                CausaRechazo.codigo == codigo.strip()
            ).first()
            if existe:
                return False, f"El código '{codigo}' ya existe"
            session.add(CausaRechazo(
                codigo=codigo.strip(),
                descripcion=descripcion.strip(),
                categoria=categoria.strip() or None,
            ))
            return True, f"Causa '{codigo}' creada"

    @staticmethod
    def actualizar_causa_rechazo(
        causa_id: int, codigo: str, descripcion: str, categoria: str = ""
    ) -> tuple[bool, str]:
        if not codigo or not codigo.strip():
            return False, "El código es obligatorio"
        if not descripcion or not descripcion.strip():
            return False, "La descripción es obligatoria"
        from src.modules.llantas.models.causa_rechazo_model import CausaRechazo
        with get_session() as session:
            causa = session.query(CausaRechazo).filter(CausaRechazo.id == causa_id).first()
            if not causa:
                return False, "Causa no encontrada"
            duplicado = session.query(CausaRechazo).filter(
                CausaRechazo.codigo == codigo.strip(),
                CausaRechazo.id != causa_id,
            ).first()
            if duplicado:
                return False, f"Ya existe otra causa con el código '{codigo}'"
            causa.codigo = codigo.strip()
            causa.descripcion = descripcion.strip()
            causa.categoria = categoria.strip() or None
            return True, "Causa actualizada"

    @staticmethod
    def eliminar_causa_rechazo(causa_id: int) -> tuple[bool, str]:
        from src.modules.llantas.models.causa_rechazo_model import CausaRechazo
        with get_session() as session:
            causa = session.query(CausaRechazo).filter(CausaRechazo.id == causa_id).first()
            if not causa:
                return False, "Causa no encontrada"
            session.delete(causa)
            return True, "Causa eliminada"
