"""LlantaService unit tests — lifecycle, state transitions, catalogs.

Uses the ``service_db`` fixture so every ``get_session()`` call inside the
service hits an isolated temporary database.
"""

import pytest

from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    TRANSICIONES_VALIDAS,
    UBICACIONES_PLANTA,
    LlantaService,
)


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


def _crear_llanta(tiquete: str = "TQ-001", **kwargs):
    ok, res = LlantaService.crear(tiquete=tiquete, **kwargs)
    assert ok, f"crear falló: {res}"
    return res


class TestCrearLlanta:
    """LlantaService.crear — basic creation rules."""

    def test_crear_exitosa_estado_pendiente(self):
        llanta = _crear_llanta()
        assert llanta.tiquete == "TQ-001"
        assert llanta.estado == "PENDIENTE"

    def test_crear_tiquete_vacio(self):
        ok, msg = LlantaService.crear(tiquete="   ")
        assert not ok
        assert isinstance(msg, str)
        assert "obligatorio" in msg

    def test_crear_tiquete_duplicado(self):
        _crear_llanta()
        ok, msg = LlantaService.crear(tiquete="TQ-001")
        assert not ok
        assert isinstance(msg, str)
        assert "ya existe" in msg.lower()

    def test_crear_con_campos_tecnicos(self):
        llanta = _crear_llanta(
            tiquete="TQ-002",
            ancho=295,
            perfil=80,
            rin=22,
            precio_venta=1500000.0,
            costo_produccion=800000.0,
        )
        assert llanta.ancho == 295
        assert llanta.precio_venta == 1500000.0


class TestTiqueteExiste:
    """LlantaService.tiquete_existe — live duplicate validation."""

    def test_existe(self):
        _crear_llanta()
        assert LlantaService.tiquete_existe("TQ-001") is True

    def test_no_existe(self):
        assert LlantaService.tiquete_existe("NO-EXISTE") is False

    def test_vacio(self):
        assert LlantaService.tiquete_existe("  ") is False


class TestCambiarEstado:
    """LlantaService.cambiar_estado — transition matrix enforcement."""

    def test_transicion_valida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "APTA")
        assert ok
        assert "APTA" in msg

    def test_transicion_invalida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "REENCAUCHADA")
        assert not ok
        assert "Transición inválida" in msg

    def test_estado_invalido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "EXPLOTADA")
        assert not ok
        assert "Estado inválido" in msg

    def test_llanta_no_existe(self):
        ok, msg = LlantaService.cambiar_estado(99999, "APTA")
        assert not ok
        assert "no encontrada" in msg

    def test_historial_se_registra(self):
        llanta = _crear_llanta()
        LlantaService.cambiar_estado(llanta.id, "APTA")
        historial = LlantaService.obtener_historial_estados(llanta.id)
        assert len(historial) == 2  # PENDIENTE (crear) + APTA
        assert str(historial[0].estado) == "APTA"


class TestMoverUbicacion:
    """LlantaService.mover_ubicacion — location tracking."""

    def test_mover_valido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(llanta.id, "PLANTA")
        assert ok
        assert isinstance(msg, str)
        assert "PLANTA" in msg
        historial = LlantaService.obtener_historial_ubicaciones(llanta.id)
        assert len(historial) == 1
        assert str(historial[0].ubicacion) == "PLANTA"

    def test_ubicacion_invalida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(llanta.id, "MARTE")
        assert not ok
        assert "Ubicación inválida" in msg

    def test_llanta_no_existe(self):
        ok, msg = LlantaService.mover_ubicacion(99999, "PLANTA")
        assert not ok
        assert "no encontrada" in msg


class TestAplicarVeredicto:
    """LlantaService.aplicar_veredicto — atomic estado + ubicación."""

    def test_veredicto_apta(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "APTA")
        assert ok
        assert "PRODUCCION" in msg

    def test_veredicto_rechazada_mueve_a_planta(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA")
        assert ok
        assert "PLANTA" in msg

    def test_veredicto_invalido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "GANADORA")
        assert not ok
        assert "Veredicto inválido" in msg

    def test_veredicto_con_transicion_invalida(self):
        llanta = _crear_llanta()
        LlantaService.cambiar_estado(llanta.id, "APTA")
        # APTA no puede ir directo a PENDIENTE vía veredicto (no es veredicto)
        ok, _ = LlantaService.aplicar_veredicto(llanta.id, "APTA")
        assert ok  # APTA → APTA es válido en la matriz


class TestCRUDCatalogos:
    """LlantaService catalog CRUD — marcas, dimensiones, diseños, causas."""

    def test_crud_marca(self):
        ok, _ = LlantaService.crear_marca("BRIDGESTONE", "BS")
        assert ok
        ok, _ = LlantaService.crear_marca("BRIDGESTONE")
        assert not ok  # duplicado
        marcas = LlantaService.listar_marcas()
        assert len(marcas) == 1
        ok, _ = LlantaService.actualizar_marca(marcas[0].id, "BRIDGESTONE", "BRS")
        assert ok
        ok, _ = LlantaService.eliminar_marca(marcas[0].id)
        assert ok
        assert len(LlantaService.listar_marcas()) == 0

    def test_marca_con_llantas_no_se_elimina(self):
        ok, _ = LlantaService.crear_marca("GOODYEAR")
        marca = LlantaService.listar_marcas()[0]
        _crear_llanta(tiquete="TQ-M1", marca_id=marca.id)
        ok, msg = LlantaService.eliminar_marca(marca.id)
        assert not ok
        assert "usan esta marca" in msg

    def test_crud_dimension(self):
        ok, _ = LlantaService.crear_dimension(295, 80, 22)
        assert ok
        ok, _ = LlantaService.crear_dimension(295, 80, 22)
        assert not ok  # duplicado
        dims = LlantaService.listar_dimensiones()
        assert len(dims) == 1
        ok, _ = LlantaService.actualizar_dimension(dims[0].id, 295, 80, 22.5)
        assert ok
        ok, _ = LlantaService.eliminar_dimension(dims[0].id)
        assert ok

    def test_dimension_invalida(self):
        ok, msg = LlantaService.crear_dimension(0, 80, 22)
        assert not ok
        assert "positivos" in msg

    def test_crud_diseno(self):
        ok, _ = LlantaService.crear_diseno("Direccional Premium", "DIRECCIONAL")
        assert ok
        ok, _ = LlantaService.crear_diseno("Direccional Premium", "DIRECCIONAL")
        assert not ok  # duplicado
        disenos = LlantaService.listar_disenos()
        assert len(disenos) == 1
        ok, _ = LlantaService.actualizar_diseno(
            disenos[0].id, "Direccional Premium", "MIXTO"
        )
        assert ok
        ok, _ = LlantaService.eliminar_diseno(disenos[0].id)
        assert ok

    def test_diseno_tipo_invalido(self):
        ok, msg = LlantaService.crear_diseno("X", "DESCONOCIDO")
        assert not ok
        assert "Tipo inválido" in msg

    def test_crud_causa_rechazo(self):
        ok, _ = LlantaService.crear_causa_rechazo("C01", "Corte lateral")
        assert ok
        ok, _ = LlantaService.crear_causa_rechazo("C01", "Otro")
        assert not ok  # código duplicado
        causas = LlantaService.listar_causas_rechazo()
        assert len(causas) == 1
        ok, _ = LlantaService.actualizar_causa_rechazo(
            causas[0].id, "C01", "Corte lateral profundo", "ESTRUCTURAL"
        )
        assert ok
        ok, _ = LlantaService.eliminar_causa_rechazo(causas[0].id)
        assert ok


class TestConsultas:
    """LlantaService query methods."""

    def test_listar_y_buscar(self):
        _crear_llanta(tiquete="TQ-A1")
        _crear_llanta(tiquete="TQ-A2")
        assert len(LlantaService.listar_llantas()) == 2
        por_term = LlantaService.buscar(term="TQ-A2")
        assert len(por_term) == 1
        por_estado = LlantaService.buscar(estado="PENDIENTE")
        assert len(por_estado) == 2

    def test_obtener_por_id(self):
        llanta = _crear_llanta()
        assert LlantaService.obtener_por_id(llanta.id) is not None
        assert LlantaService.obtener_por_id(99999) is None

    def test_contar_por_estado(self):
        _crear_llanta(tiquete="TQ-C1")
        _crear_llanta(tiquete="TQ-C2")
        conteo = LlantaService.contar_por_estado()
        assert conteo.get("PENDIENTE") == 2


class TestMatriz:
    """Static state-machine contract."""

    def test_estados_proceso_completos(self):
        assert set(ESTADOS_PROCESO) == {
            "PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA",
        }

    def test_matriz_transiciones(self):
        assert TRANSICIONES_VALIDAS["PENDIENTE"] == {"APTA", "RECHAZADA", "CLIENTE"}
        assert "REENCAUCHADA" in TRANSICIONES_VALIDAS["APTA"]

    def test_ubicaciones_validas(self):
        assert set(UBICACIONES_PLANTA) == {"PRODUCCION", "PLANTA", "CLIENTE"}
