from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service import LlantaService


class LlantaViewModel:
    """ViewModel for tire operations (MVVM pattern)."""

    def __init__(self) -> None:
        self._llantas: list[Llanta] = []
        self._filtro: str = ""
        self._filtro_estado: str | None = None

    @property
    def llantas(self) -> list[Llanta]:
        return self._llantas

    @property
    def filtro(self) -> str:
        return self._filtro

    @filtro.setter
    def filtro(self, valor: str) -> None:
        self._filtro = valor

    @property
    def filtro_estado(self) -> str | None:
        return self._filtro_estado

    @filtro_estado.setter
    def filtro_estado(self, valor: str | None) -> None:
        self._filtro_estado = valor

    def cargar_llantas(self) -> None:
        if self._filtro or self._filtro_estado:
            self._llantas = LlantaService.buscar(
                term=self._filtro,
                estado=self._filtro_estado,
            )
        else:
            self._llantas = LlantaService.listar_llantas()

    def buscar(self, termino: str) -> list[Llanta]:
        self._filtro = termino
        self.cargar_llantas()
        return self._llantas

    def filtrar_por_estado(self, estado: str | None) -> list[Llanta]:
        self._filtro_estado = estado
        self.cargar_llantas()
        return self._llantas

    def crear(
        self,
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
        numero_orden: str | None = None,
        consecutivo: str | None = None,
        dot: str | None = None,
        observaciones: str | None = None,
        fecha_ingreso=None,
    ) -> tuple[bool, str]:
        ok, resultado = LlantaService.crear(
            tiquete=tiquete,
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
            cliente_id=cliente_id,
            numero_orden=numero_orden,
            consecutivo=consecutivo,
            dot=dot,
            observaciones=observaciones,
            fecha_ingreso=fecha_ingreso,
        )
        if ok:
            self.cargar_llantas()
            assert isinstance(resultado, Llanta)
            return True, f"Llanta '{resultado.tiquete}' creada"
        return False, str(resultado)

    def cambiar_estado(self, llanta_id: int, estado: str) -> tuple[bool, str]:
        resultado = LlantaService.cambiar_estado(llanta_id, estado)
        if resultado[0]:
            self.cargar_llantas()
        return resultado

    def mover_ubicacion(
        self, llanta_id: int, ubicacion: str
    ) -> tuple[bool, str]:
        return LlantaService.mover_ubicacion(llanta_id, ubicacion)

    def obtener_por_id(self, llanta_id: int) -> Llanta | None:
        return LlantaService.obtener_por_id(llanta_id)
