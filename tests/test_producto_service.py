"""Tests de ProductoService para la categoría CONSUMIBLE."""

from decimal import Decimal

import pytest

from src.modules.inventario.services.inventario_kpi_service import InventarioKpiService
from src.modules.inventario.services.producto_service import ProductoService


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


class TestCrearConsumible:
    """crear() con categoria CONSUMIBLE."""

    def test_crear_consumible(self):
        ok, res = ProductoService.crear(
            nombre="Guantes de seguridad",
            sku="CNS-GUANTES",
            categoria="CONSUMIBLE",
            costo_unitario=Decimal("12000"),
            stock_inicial=Decimal("50"),
            stock_kg=Decimal("0"),
            stock_minimo=Decimal("10"),
            unidad_medida="CAJA",
        )
        assert ok is True
        assert res.categoria == "CONSUMIBLE"
        assert float(res.stock) == 50.0
        assert float(res.costo_unitario) == 12000.0

    def test_consumible_no_aparece_en_materias_primas(self):
        ok, _ = ProductoService.crear(
            nombre="Cinta de enmascarar",
            sku="CNS-CINTA",
            categoria="CONSUMIBLE",
        )
        assert ok is True
        mp = InventarioKpiService.materias_primas()
        cons = InventarioKpiService.consumibles()
        assert all(p.categoria == "MATERIA_PRIMA" for p in mp)
        assert any(p.sku == "CNS-CINTA" for p in cons)

    def test_categoria_consumible_en_catalogo(self):
        assert "CONSUMIBLE" in ProductoService.CATEGORIAS

    def test_sku_duplicado_entre_categorias_rechazado(self):
        ok, _ = ProductoService.crear(
            nombre="Producto A", sku="SKU-DUP", categoria="MATERIA_PRIMA"
        )
        assert ok is True
        ok2, msg = ProductoService.crear(
            nombre="Producto B", sku="SKU-DUP", categoria="CONSUMIBLE"
        )
        assert ok2 is False
        assert "SKU" in msg