from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository
from src.modules.llantas.services.llanta_service._constantes import (
    COMBINACIONES_VALIDAS,
    DISENO_REPARADA,
    ESTADOS_PROCESO,
    TRANSICIONES_VALIDAS,
    UBICACIONES_PLANTA,
    VEREDICTO_UBICACION,
)


def formatear_tiquete(tiquete: str | None) -> str:
    """Devuelve el tiquete SIN el prefijo fijo 'J' de la serie (presentación).

    La BD almacena el tiquete con el prefijo (ej. 'J24537'); en pantalla se
    muestra solo el número ('24537'). NO modifica el dato almacenado.
    """
    if not tiquete:
        return ""
    return tiquete.removeprefix("J")


def formatear_orden(numero_orden: str | None, consecutivo: str | None = None) -> str:
    """Orden de servicio con su consecutivo (1-12 por orden): '64230C-1'.

    Una orden agrupa hasta 12 tiquetes; cada tiquete lleva su consecutivo en
    la casilla correspondiente. Sin consecutivo devuelve solo la orden.
    """
    orden = (numero_orden or "").strip()
    if not orden:
        return ""
    cons = (consecutivo or "").strip()
    return f"{orden}-{cons}" if cons else orden


class _GestionLlantasMixin:
    """Gestión del ciclo de vida de llantas: consulta, creación,
    transiciones de estado y movimientos de ubicación."""

    @staticmethod
    def listar_llantas(
        limite: int | None = None, offset: int = 0
    ) -> tuple[list[Llanta], int]:
        """Lista llantas con paginación opcional.

        Devuelve (llantas, total_registros). Con limite=None devuelve todas.
        """
        with get_session() as session:
            total = session.query(Llanta).count()
            query = session.query(Llanta).order_by(Llanta.id.desc())
            if limite is not None:
                query = query.limit(limite).offset(offset)
            llantas = query.all()
            for ll in llantas:
                session.expunge(ll)
            return llantas, total

    @staticmethod
    def buscar(
        term: str = "",
        estado: str | None = None,
        cliente_id: int | None = None,
        limite: int | None = None,
        offset: int = 0,
    ) -> tuple[list[Llanta], int]:
        """Búsqueda con paginación opcional.

        Devuelve (llantas, total_registros). Con limite=None devuelve todas.
        """
        with get_session() as session:
            query = session.query(Llanta)

            if term:
                pattern = f"%{term}%"
                query = query.outerjoin(
                    Cliente, Llanta.cliente_id == Cliente.id
                ).filter(
                    Llanta.tiquete.ilike(pattern)
                    | Llanta.marca.ilike(pattern)
                    | Llanta.dimension.ilike(pattern)
                    | Cliente.nombre.ilike(pattern)
                    | Cliente.nit.ilike(pattern)
                )

            if estado:
                query = query.filter(Llanta.estado == estado)

            if cliente_id is not None:
                query = query.filter(Llanta.cliente_id == cliente_id)

            total = query.count()
            query = query.order_by(Llanta.id.desc())
            if limite is not None:
                query = query.limit(limite).offset(offset)
            llantas = query.all()
            for ll in llantas:
                session.expunge(ll)
            return llantas, total

    @staticmethod
    def obtener_por_id(llanta_id: int) -> Llanta | None:
        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if llanta:
                session.expunge(llanta)
            return llanta

    @staticmethod
    def obtener_por_tiquete(tiquete: str) -> Llanta | None:
        with get_session() as session:
            llanta = LlantaRepository.get_by_tiquete(session, (tiquete or "").strip())
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
                ubicacion_actual="PLANTA",
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

            # Create initial ubicacion (ingreso = Planta según flujo correcto 2)
            historial_ubicacion = UbicacionLlanta(
                llanta_id=llanta.id, ubicacion="PLANTA"
            )
            session.add(historial_ubicacion)

            session.expunge(llanta)
            return True, llanta

    @staticmethod
    def actualizar_llanta(
        llanta_id: int,
        cliente_id: int | None = None,
        diseno_id: int | None = None,
        numero_orden: str | None = None,
        consecutivo: str | None = None,
        marca_id: int | None = None,
        dimension_id: int | None = None,
        dot: str | None = None,
        asesor: str | None = None,
        observaciones: str | None = None,
        fecha_ingreso=None,
    ) -> tuple[bool, str]:
        """Actualiza características editables de una llanta.

        NO modifica: tiquete, precio_venta ni costo_produccion (bloqueados).
        Registra la edición en auditoría.
        """
        from src.core.services.audit_service import registrar_crud
        from src.core.services.session_service import get_session_manager

        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if not llanta:
                return False, "Llanta no encontrada"

            # Textos legacy (para reportes que usan l.marca / l.dimension)
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

            llanta.cliente_id = cliente_id
            llanta.diseno_id = diseno_id
            llanta.numero_orden = numero_orden
            llanta.consecutivo = consecutivo
            llanta.marca_id = marca_id
            llanta.marca = marca_text
            llanta.dimension_id = dimension_id
            llanta.dimension = dimension_text
            llanta.dot = dot
            llanta.asesor = asesor
            llanta.observaciones = observaciones
            if fecha_ingreso is not None:
                llanta.fecha_ingreso = fecha_ingreso

            # Auditoría (solo si hay usuario en sesión — no romper si no existe)
            uid = get_session_manager().get_user_id()
            if uid is not None:
                registrar_crud(
                    usuario_id=uid,
                    entidad="llanta",
                    accion="UPDATE",
                    objeto_id=llanta.id,
                    cambios={
                        "cliente_id": cliente_id,
                        "diseno_id": diseno_id,
                        "numero_orden": numero_orden,
                        "consecutivo": consecutivo,
                    },
                    session=session,
                )
            return True, f"Llanta '{llanta.tiquete}' actualizada"

    @staticmethod
    def cambiar_estado(
        llanta_id: int, nuevo_estado: str, causa_rechazo_id: int | None = None
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

            # Causa de rechazo obligatoria cuando el estado es RECHAZADA
            # (ESPECIFICACIONES_DELCA_v2.1.docx — sección 5.1)
            if nuevo_estado == "RECHAZADA":
                if causa_rechazo_id is None:
                    return False, (
                        "Debe seleccionar la causa de rechazo para cambiar "
                        "el estado a RECHAZADA"
                    )
                causa = LlantaRepository.obtener_causa_rechazo(
                    session, causa_rechazo_id
                )
                if not causa:
                    return False, "La causa de rechazo seleccionada no existe"

            llanta.estado = nuevo_estado
            llanta.causa_rechazo_id = (
                causa_rechazo_id if nuevo_estado == "RECHAZADA" else None
            )
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

            # Validar combinación estado ↔ ubicación (reglas R1-R4, R6)
            estado_actual = llanta.estado or "PENDIENTE"
            permitidas = COMBINACIONES_VALIDAS.get(estado_actual, set())
            if ubicacion not in permitidas:
                return False, (
                    f"Ubicación inválida: la llanta en estado '{estado_actual}' "
                    f"no puede estar en '{ubicacion}'"
                )

            movimiento = UbicacionLlanta(
                llanta_id=llanta_id, ubicacion=ubicacion
            )
            session.add(movimiento)
            llanta.ubicacion_actual = ubicacion
            return True, f"Llanta movida a '{ubicacion}'"

    @staticmethod
    def aplicar_veredicto(
        llanta_id: int, veredicto: str, causa_rechazo_id: int | None = None
    ) -> tuple[bool, str]:
        """Aplica un veredicto de inspección: cambia estado y ubicación
        de forma atómica según "flujo correcto 2".

        Veredictos válidos:
          - APTA         → estado APTA, ubicación PRODUCCION
          - REENCAUCHADA → estado REENCAUCHADA, ubicación PLANTA
          - REPARADA     → estado REPARADA, ubicación PLANTA (solo diseño REP)
          - RECHAZADA    → estado RECHAZADA, ubicación PLANTA (causa obligatoria)
          - REPROCESO    → estado REPROCESO, ubicación PRODUCCION (R7)
        """
        if veredicto not in VEREDICTO_UBICACION:
            return False, (
                f"Veredicto inválido: {veredicto}. "
                f"Válidos: {', '.join(VEREDICTO_UBICACION)}"
            )

        with get_session() as session:
            llanta = LlantaRepository.get_by_id(session, llanta_id)
            if not llanta:
                return False, "Llanta no encontrada"

            # La causa de rechazo es OBLIGATORIA solo en la inspección inicial
            # (cambiar_estado). En la inspección final (veredicto) no se exige;
            # si se pasa una causa_rechazo_id válida, se guarda.
            if veredicto == "RECHAZADA" and causa_rechazo_id is not None:
                causa = LlantaRepository.obtener_causa_rechazo(
                    session, causa_rechazo_id
                )
                if not causa:
                    return False, "La causa de rechazo seleccionada no existe"

            # Regla R5: REPARADA solo cuando el diseño de banda es REP
            if veredicto == "REPARADA":
                diseno_nombre = (
                    llanta.diseno_obj.nombre if llanta.diseno_obj else None
                )
                if diseno_nombre != DISENO_REPARADA:
                    return False, (
                        f"Reparada solo se permite con diseño de banda "
                        f"'{DISENO_REPARADA}' (diseño actual: "
                        f"{diseno_nombre or 'sin diseño'})"
                    )

            # Validar transición según la matriz del flujo
            estado_actual = llanta.estado or "PENDIENTE"
            permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
            if veredicto not in permitidos:
                return False, (
                    f"Transición inválida: '{estado_actual}' no puede pasar "
                    f"directamente a '{veredicto}'"
                )

            # Estado + ubicación en la misma transacción
            nueva_ubicacion = VEREDICTO_UBICACION[veredicto]
            llanta.estado = veredicto
            llanta.ubicacion_actual = nueva_ubicacion
            llanta.causa_rechazo_id = (
                causa_rechazo_id if veredicto == "RECHAZADA" else None
            )

            session.add(
                EstadoLlanta(llanta_id=llanta_id, estado=veredicto)
            )
            session.add(
                UbicacionLlanta(
                    llanta_id=llanta_id,
                    ubicacion=nueva_ubicacion,
                )
            )
            return True, (
                f"Veredicto '{veredicto}' aplicado — "
                f"ubicación: {nueva_ubicacion}"
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