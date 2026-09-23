"""Tests de ProductoService para la categoría CONSUMIBLE."""

from decimal import Decimal

import pytest

from src.modules.inventario.models.producto_model import Producto
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
        ok2, res2 = ProductoService.crear(
            nombre="Producto B", sku="SKU-DUP", categoria="CONSUMIBLE"
        )
        assert ok2 is False
        assert "SKU" in str(res2)


class TestValorInventarioPorKg:
    """El costo de bandas (ROLLO) es por KG → valor = stock_kg × costo."""

    def test_banda_rollo_valor_usando_kg(self):
        ok, res = ProductoService.crear(
            nombre="Banda TEST 100",
            sku="BND-TEST100",
            categoria="MATERIA_PRIMA",
            costo_unitario=Decimal("19000"),
            stock_inicial=Decimal("10"),
            stock_kg=Decimal("400"),
            unidad_medida="ROLLO",
        )
        assert ok is True
        assert isinstance(res, Producto)
        # 400 kg × $19,000 = $7,600,000 (no 10 × 19,000 = 190,000)
        assert ProductoService.valor_inventario_producto(res) == 400.0 * 19000.0

    def test_unidad_caja_valor_por_unidad(self):
        ok, res = ProductoService.crear(
            nombre="Guantes TEST",
            sku="CNS-GT-TEST",
            categoria="CONSUMIBLE",
            costo_unitario=Decimal("12000"),
            stock_inicial=Decimal("50"),
            stock_kg=Decimal("0"),
            unidad_medida="CAJA",
        )
        assert ok is True
        assert isinstance(res, Producto)
        # 50 und × $12,000 = $600,000 (stock_kg es 0, no aplica)
        assert ProductoService.valor_inventario_producto(res) == 50.0 * 12000.0

    def test_kpi_valor_inventario_usa_kg_para_bandas(self):
        ok, _ = ProductoService.crear(
            nombre="Banda KPI 250",
            sku="BND-KPI250",
            categoria="MATERIA_PRIMA",
            costo_unitario=Decimal("20000"),
            stock_inicial=Decimal("5"),
            stock_kg=Decimal("250"),
            unidad_medida="ROLLO",
        )
        assert ok is True
        kpis = InventarioKpiService.resumen_kpis()
        # 250 kg × $20,000 = $5,000,000 (no 5 × 20,000 = 100,000)
        assert kpis["valor_inventario"] >= 5_000_000.0