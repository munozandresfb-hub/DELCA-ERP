from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service import LlantaService


class LlantaViewModel:
    """ViewModel for tire operations (MVVM pattern)."""

    PAGE_SIZE = 500

    def __init__(self) -> None:
        self._llantas: list[Llanta] = []
        self._filtro: str = ""
        self._filtro_estado: str | None = None
        self._filtro_cliente: int | None = None
        self._filtro_dimension: int | None = None
        self._filtro_diseno: int | None = None
        self._filtro_marca: int | None = None
        self._filtro_ubicacion: str | None = None
        self._pagina: int = 0
        self._total: int = 0

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

    @property
    def pagina(self) -> int:
        return self._pagina

    @property
    def total(self) -> int:
        return self._total

    @property
    def hay_mas(self) -> bool:
        """True si existen más registros después de la página actual."""
        return (self._pagina + 1) * self.PAGE_SIZE < self._total

    def cargar_llantas(self, pagina: int | None = None) -> None:
        if pagina is not None:
            self._pagina = pagina
        offset = self._pagina * self.PAGE_SIZE
        if (
            self._filtro
            or self._filtro_estado
            or self._filtro_cliente is not None
            or self._filtro_dimension is not None
            or self._filtro_diseno is not None
            or self._filtro_marca is not None
            or self._filtro_ubicacion
        ):
            self._llantas, self._total = LlantaService.buscar(
                term=self._filtro,
                estado=self._filtro_estado,
                cliente_id=self._filtro_cliente,
                dimension_id=self._filtro_dimension,
                diseno_id=self._filtro_diseno,
                marca_id=self._filtro_marca,
                ubicacion=self._filtro_ubicacion,
                limite=self.PAGE_SIZE,
                offset=offset,
            )
        else:
            self._llantas, self._total = LlantaService.listar_llantas(
                limite=self.PAGE_SIZE, offset=offset
            )

    def buscar(self, termino: str) -> list[Llanta]:
        self._filtro = termino
        self._pagina = 0
        self.cargar_llantas()
        return self._llantas

    def filtrar_por_estado(self, estado: str | None) -> list[Llanta]:
        self._filtro_estado = estado
        self._pagina = 0
        self.cargar_llantas()
        return self._llantas

    def buscar_avanzada(
        self,
        cliente_id: int | None = None,
        dimension_id: int | None = None,
        diseno_id: int | None = None,
        marca_id: int | None = None,
        estado: str | None = None,
        ubicacion: str | None = None,
    ) -> list[Llanta]:
        """Búsqueda con varios criterios combinados (todos AND)."""
        self._filtro_cliente = cliente_id
        self._filtro_dimension = dimension_id
        self._filtro_diseno = diseno_id
        self._filtro_marca = marca_id
        self._filtro_estado = estado
        self._filtro_ubicacion = ubicacion
        self._pagina = 0
        self.cargar_llantas()
        return self._llantas

    def limpiar_filtros_avanzados(self) -> list[Llanta]:
        """Limpia los filtros de búsqueda avanzada (todos los criterios)."""
        self._filtro_cliente = None
        self._filtro_dimension = None
        self._filtro_diseno = None
        self._filtro_marca = None
        self._filtro_estado = None
        self._filtro_ubicacion = None
        self._pagina = 0
        self.cargar_llantas()
        return self._llantas

    def siguiente_pagina(self) -> None:
        if self.hay_mas:
            self._pagina += 1
            self.cargar_llantas()

    def pagina_anterior(self) -> None:
        if self._pagina > 0:
            self._pagina -= 1
            self.cargar_llantas()

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

    def actualizar(self, llanta_id: int, **datos) -> tuple[bool, str]:
        """Actualiza características editables de una llanta (cliente, diseño,
        número de orden, marca, dimensión, dot, asesor, observaciones...)."""
        ok, resultado = LlantaService.actualizar_llanta(llanta_id, **datos)
        if ok:
            self.cargar_llantas()
            return True, str(resultado)
        return False, str(resultado)

    def obtener_por_tiquete(self, tiquete: str) -> Llanta | None:
        """Busca una llanta por su tiquete (para imprimir la recién creada)."""
        return LlantaService.obtener_por_tiquete(tiquete)

    def cambiar_estado(self, llanta_id: int, estado: str) -> tuple[bool, str]:
        resultado = LlantaService.cambiar_estado(llanta_id, estado)
        if resultado[0]:
            self.cargar_llantas()
        return resultado

    def aplicar_veredicto(
        self, llanta_id: int, veredicto: str
    ) -> tuple[bool, str]:
        resultado = LlantaService.aplicar_veredicto(llanta_id, veredicto)
        if resultado[0]:
            self.cargar_llantas()
        return resultado

    def mover_ubicacion(
        self, llanta_id: int, ubicacion: str
    ) -> tuple[bool, str]:
        return LlantaService.mover_ubicacion(llanta_id, ubicacion)

    def obtener_por_id(self, llanta_id: int) -> Llanta | None:
        return LlantaService.obtener_por_id(llanta_id)

    def eliminar(self, llanta_id: int) -> tuple[bool, str]:
        """Elimina una llanta (solo ADMIN). Recarga la lista si tuvo éxito."""
        resultado = LlantaService.eliminar(llanta_id)
        if resultado[0]:
            self.cargar_llantas()
        return resultado
