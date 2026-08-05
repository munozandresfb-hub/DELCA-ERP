from src.modules.clientes.models.cliente_model import Cliente
from src.modules.clientes.services.cliente_service import ClienteService


class ClienteViewModel:
    """ViewModel for client operations (MVVM pattern)."""

    def __init__(self) -> None:
        self._clientes: list[Cliente] = []
        self._filtro: str = ""

    @property
    def clientes(self) -> list[Cliente]:
        return self._clientes

    @property
    def filtro(self) -> str:
        return self._filtro

    @filtro.setter
    def filtro(self, valor: str) -> None:
        self._filtro = valor

    def cargar_clientes(self) -> None:
        if self._filtro:
            self._clientes = ClienteService.buscar(self._filtro)
        else:
            self._clientes = ClienteService.listar_clientes()

    def buscar(self, termino: str) -> list[Cliente]:
        self._filtro = termino
        self.cargar_clientes()
        return self._clientes

    def crear(
        self,
        nombre: str,
        nit: str,
        celular: str | None = None,
        email: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
    ) -> tuple[bool, str]:
        ok, resultado = ClienteService.crear(
            nombre=nombre,
            nit=nit,
            celular=celular,
            email=email,
            direccion=direccion,
            ciudad=ciudad,
        )
        if ok:
            self.cargar_clientes()
            assert isinstance(resultado, Cliente)
            return True, f"Cliente '{resultado.nombre}' creado"
        return False, str(resultado)

    def actualizar(
        self,
        cliente_id: int,
        nombre: str,
        nit: str,
        celular: str | None = None,
        email: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
        activo: bool = True,
        categoria_abc: str = "B",
    ) -> tuple[bool, str | Cliente]:
        return ClienteService.actualizar(
            cliente_id=cliente_id,
            nombre=nombre,
            nit=nit,
            celular=celular,
            email=email,
            direccion=direccion,
            ciudad=ciudad,
            activo=activo,
            categoria_abc=categoria_abc,
        )

    def eliminar(self, cliente_id: int) -> tuple[bool, str]:
        resultado = ClienteService.eliminar(cliente_id)
        if resultado[0]:
            self.cargar_clientes()
        return resultado

    def obtener_por_id(self, cliente_id: int) -> Cliente | None:
        return ClienteService.obtener_por_id(cliente_id)
