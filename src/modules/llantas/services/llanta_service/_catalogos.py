from src.database.engine import get_session
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository


class _CatalogosMixin:
    """CRUD de catálogos maestros: marcas, dimensiones, diseños de banda
    y causas de rechazo."""

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