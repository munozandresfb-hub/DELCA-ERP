"""Tests de PrecioProductoService.aplicar_precios() — copia precio_normal → precio_venta."""

from decimal import Decimal

import pytest

from src.modules.inventario.services.precio_producto_service import PrecioProductoService
from src.modules.llantas.services.llanta_service import LlantaService


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


def _crear_llanta_terminada(tiquete: str, diseno_id, dimension_id, precio_venta=None):
    ok, res = LlantaService.crear(
        tiquete=tiquete, diseno_id=diseno_id, dimension_id=dimension_id,
        precio_venta=precio_venta,
    )
    assert ok, f"crear falló: {res}"
    # Llevar a REENCAUCHADA (terminada)
    ok, msg = LlantaService.aplicar_veredicto(res.id, "APTA")
    assert ok, msg
    ok, msg = LlantaService.aplicar_veredicto(res.id, "REENCAUCHADA")
    assert ok, msg
    return LlantaService.obtener_por_id(res.id)


def _precio_de(llanta) -> float | None:
    p = llanta.precio_venta
    return float(p) if p is not None else None


def _preparar_catalogo_y_precio():
    """Crea diseño + dimensión + precio en catálogo."""
    ok, _ = LlantaService.crear_diseno("D-100", "MIXTO")
    disenos = LlantaService.listar_disenos()
    diseno = next(d for d in disenos if d.nombre == "D-100")
    ok, _ = LlantaService.crear_dimension(295, 80, 22.5)
    dims = LlantaService.listar_dimensiones()
    dim = next(d for d in dims if d.ancho == 295)
    ok, _ = PrecioProductoService.guardar(
        diseno.id, dim.id,
        costo_fabricacion=Decimal("800000"),
        precio_minimo=Decimal("900000"),
        precio_medio=Decimal("950000"),
        precio_normal=Decimal("1000000"),
    )
    return diseno, dim


class TestAplicarPrecios:
    """aplicar_precios() — copia precio_normal a precio_venta si está vacío."""

    def test_copia_precio_normal_a_terminada(self):
        diseno, dim = _preparar_catalogo_y_precio()
        llanta = _crear_llanta_terminada("P-001", diseno.id, dim.id)

        ok, msg = PrecioProductoService.aplicar_precios(llanta_id=llanta.id)
        assert ok
        assert "aplicados: 1" in msg

        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert _precio_de(llanta_actual) == 1000000.0

    def test_no_toca_sin_cobertura(self):
        # Diseño sin precio en catálogo → no se aplica nada
        ok, _ = LlantaService.crear_diseno("SIN-PRECIO", "MIXTO")
        diseno = next(d for d in LlantaService.listar_disenos() if d.nombre == "SIN-PRECIO")
        ok, _ = LlantaService.crear_dimension(315, 80, 22.5)
        dim = next(d for d in LlantaService.listar_dimensiones() if d.ancho == 315)
        llanta = _crear_llanta_terminada("P-002", diseno.id, dim.id)

        ok, msg = PrecioProductoService.aplicar_precios(llanta_id=llanta.id)
        assert ok
        assert "sin cobertura: 1" in msg

        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert _precio_de(llanta_actual) is None

    def test_no_pisa_precio_existente(self):
        diseno, dim = _preparar_catalogo_y_precio()
        llanta = _crear_llanta_terminada("P-003", diseno.id, dim.id, precio_venta=500000)

        ok, msg = PrecioProductoService.aplicar_precios(llanta_id=llanta.id)
        assert ok
        assert "ya tenían: 1" in msg

        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert _precio_de(llanta_actual) == 500000.0  # no se pisó

    def test_idempotente(self):
        diseno, dim = _preparar_catalogo_y_precio()
        llanta = _crear_llanta_terminada("P-004", diseno.id, dim.id)

        PrecioProductoService.aplicar_precios(llanta_id=llanta.id)
        # Segunda ejecución: ya tiene precio → 0 aplicados
        ok, msg = PrecioProductoService.aplicar_precios(llanta_id=llanta.id)
        assert ok
        assert "aplicados: 0" in msg
        assert "ya tenían: 1" in msg