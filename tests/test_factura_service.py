"""FacturaService unit tests — invoice creation, payments, voiding, cartera.

Uses the ``service_db`` fixture so every ``get_session()`` call inside the
service hits an isolated temporary database.
"""

from decimal import Decimal

import pytest

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.llantas.services.llanta_service import LlantaService


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


def _crear_cliente(nombre: str = "Cliente Test", nit: str = "900123456") -> int:
    with get_session() as session:
        cliente = Cliente(nombre=nombre, nit=nit)
        session.add(cliente)
        session.flush()
        return cliente.id


def _crear_llanta(tiquete: str = "FAC-TQ-001") -> int:
    ok, llanta = LlantaService.crear(tiquete=tiquete)
    assert ok, f"crear llanta falló: {llanta}"
    return llanta.id


def _crear_factura(cliente_id: int, llanta_id: int, total: str = "1000") -> int:
    ok, res = FacturaService.crear(
        cliente_id=cliente_id,
        total=Decimal(total),
        items=[{"llanta_id": llanta_id, "precio_unitario": Decimal(total)}],
    )
    assert ok, f"crear factura falló: {res}"
    return res.id


class TestCrearFactura:
    """FacturaService.crear — validation and side effects."""

    def test_crear_exitosa(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        factura = FacturaService.obtener_por_id(factura_id)
        assert factura is not None
        assert factura.estado == "PENDIENTE"
        assert factura.total == Decimal("1000")
        assert factura.saldo == Decimal("1000")

    def test_crear_sin_cliente(self):
        ok, msg = FacturaService.crear(cliente_id=0, total=Decimal("1000"))
        assert not ok
        assert isinstance(msg, str)
        assert "cliente" in msg

    def test_crear_total_invalido(self):
        cliente_id = _crear_cliente()
        ok, msg = FacturaService.crear(cliente_id=cliente_id, total=Decimal("0"))
        assert not ok
        assert isinstance(msg, str)
        assert "total" in msg

    def test_crear_cliente_inexistente(self):
        ok, msg = FacturaService.crear(cliente_id=99999, total=Decimal("1000"))
        assert not ok
        assert isinstance(msg, str)
        assert "Cliente no encontrado" in msg

    def test_crear_llanta_inexistente(self):
        cliente_id = _crear_cliente()
        ok, msg = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("1000"),
            items=[{"llanta_id": 99999, "precio_unitario": Decimal("1000")}],
        )
        assert not ok
        assert isinstance(msg, str)
        assert "no existen" in msg

    def test_crear_misma_llanta_dos_veces(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        ok, msg = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("2000"),
            items=[
                {"llanta_id": llanta_id, "precio_unitario": Decimal("1000")},
                {"llanta_id": llanta_id, "precio_unitario": Decimal("1000")},
            ],
        )
        assert not ok
        assert isinstance(msg, str)
        assert "dos veces" in msg

    def test_crear_actualiza_saldo_cliente(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id)
        with get_session() as session:
            cliente = session.query(Cliente).filter(Cliente.id == cliente_id).first()
            assert cliente is not None
            assert cliente.saldo == Decimal("1000")


class TestCrearFacturaLlantaNueva:
    """FacturaService.crear — manual 'llanta nueva' items (descripcion sin llanta_id)."""

    def test_crear_con_llanta_nueva_manual(self):
        cliente_id = _crear_cliente()
        ok, res = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("1500"),
            items=[
                {"descripcion": "Goodyear 295/80 R22.5 nueva", "precio_unitario": Decimal("1500")}
            ],
        )
        assert ok, f"crear factura falló: {res}"
        factura = FacturaService.obtener_por_id(res.id)
        assert factura is not None
        assert len(factura.llantas_detalle) == 1
        item = factura.llantas_detalle[0]
        assert item.llanta_id is None
        assert item.descripcion == "Goodyear 295/80 R22.5 nueva"
        assert item.precio_unitario == Decimal("1500")

    def test_crear_mixto_reencauchada_y_nueva(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        ok, res = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("2500"),
            items=[
                {"llanta_id": llanta_id, "precio_unitario": Decimal("1000")},
                {"descripcion": "Michelin 315/80 R22.5 nueva", "precio_unitario": Decimal("1500")},
            ],
        )
        assert ok, f"crear factura falló: {res}"
        factura = FacturaService.obtener_por_id(res.id)
        assert factura is not None
        assert len(factura.llantas_detalle) == 2
        tipos = {(it.llanta_id, it.descripcion) for it in factura.llantas_detalle}
        assert (llanta_id, None) in tipos
        assert (None, "Michelin 315/80 R22.5 nueva") in tipos

    def test_item_sin_llanta_ni_descripcion_rechazado(self):
        cliente_id = _crear_cliente()
        ok, msg = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("1000"),
            items=[{"precio_unitario": Decimal("1000")}],
        )
        assert not ok
        assert isinstance(msg, str)
        assert "descripción" in msg

    def test_descripcion_vacia_rechazada(self):
        cliente_id = _crear_cliente()
        ok, msg = FacturaService.crear(
            cliente_id=cliente_id,
            total=Decimal("1000"),
            items=[{"descripcion": "   ", "precio_unitario": Decimal("1000")}],
        )
        assert not ok
        assert isinstance(msg, str)
        assert "descripción" in msg


class TestLlantasFacturables:
    """FacturaService.listar_llantas_facturables — once-billed rule."""

    def test_llanta_sin_facturar_disponible(self):
        llanta_id = _crear_llanta()
        disponibles = FacturaService.listar_llantas_facturables()
        assert any(l.id == llanta_id for l in disponibles)

    def test_llanta_facturada_excluida(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id)
        disponibles = FacturaService.listar_llantas_facturables()
        assert all(l.id != llanta_id for l in disponibles)

    def test_llanta_disponible_tras_anulacion(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, _ = FacturaService.anular(factura_id)
        assert ok
        disponibles = FacturaService.listar_llantas_facturables()
        assert any(l.id == llanta_id for l in disponibles)


class TestPagos:
    """FacturaService.registrar_pago — payment validation."""

    def test_pago_parcial(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, msg = FacturaService.registrar_pago(factura_id, Decimal("400"))
        assert ok
        assert isinstance(msg, str)
        factura = FacturaService.obtener_por_id(factura_id)
        assert factura is not None
        assert factura.saldo == Decimal("600")
        assert factura.estado == "PENDIENTE"

    def test_pago_completo_marca_pagada(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, _ = FacturaService.registrar_pago(factura_id, Decimal("1000"))
        assert ok
        factura = FacturaService.obtener_por_id(factura_id)
        assert factura is not None
        assert factura.saldo == Decimal("0")
        assert factura.estado == "PAGADA"

    def test_pago_excede_saldo(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, msg = FacturaService.registrar_pago(factura_id, Decimal("1500"))
        assert not ok
        assert isinstance(msg, str)
        assert "supera" in msg

    def test_pago_valor_negativo(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, msg = FacturaService.registrar_pago(factura_id, Decimal("-50"))
        assert not ok
        assert isinstance(msg, str)
        assert "mayor a cero" in msg

    def test_pago_en_factura_anulada(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        FacturaService.anular(factura_id)
        ok, msg = FacturaService.registrar_pago(factura_id, Decimal("100"))
        assert not ok
        assert isinstance(msg, str)
        assert "anuladas" in msg

    def test_obtener_pagos(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        FacturaService.registrar_pago(factura_id, Decimal("400"))
        pagos = FacturaService.obtener_pagos(factura_id)
        assert len(pagos) == 1
        assert pagos[0].valor == Decimal("400")


class TestAnular:
    """FacturaService.anular — voiding rules."""

    def test_anular_revierte_saldo_cliente(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        ok, _ = FacturaService.anular(factura_id)
        assert ok
        factura = FacturaService.obtener_por_id(factura_id)
        assert factura is not None
        assert factura.estado == "ANULADA"
        with get_session() as session:
            cliente = session.query(Cliente).filter(Cliente.id == cliente_id).first()
            assert cliente is not None
            assert cliente.saldo == Decimal("0")

    def test_anular_dos_veces(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        FacturaService.anular(factura_id)
        ok, msg = FacturaService.anular(factura_id)
        assert not ok
        assert isinstance(msg, str)
        assert "ya está anulada" in msg

    def test_anular_pagada_rechazada(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        FacturaService.registrar_pago(factura_id, Decimal("1000"))
        ok, msg = FacturaService.anular(factura_id)
        assert not ok
        assert isinstance(msg, str)
        assert "pagada" in msg


class TestConsultas:
    """FacturaService query methods."""

    def test_listar_por_estado(self):
        cliente_id = _crear_cliente()
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        pendientes = FacturaService.listar_facturas(estado="PENDIENTE")
        assert any(f.id == factura_id for f in pendientes)
        anuladas = FacturaService.listar_facturas(estado="ANULADA")
        assert all(f.id != factura_id for f in anuladas)

    def test_buscar_por_termino(self):
        cliente_id = _crear_cliente(nombre="Empresa Alpha", nit="900000111")
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id)
        por_nombre = FacturaService.buscar(termino="Alpha")
        assert any(f.id == factura_id for f in por_nombre)
        por_nit = FacturaService.buscar(termino="900000111")
        assert any(f.id == factura_id for f in por_nit)

    def test_obtener_cartera_clientes(self):
        cliente_id = _crear_cliente(nombre="Deudor SA", nit="900000222")
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id, total="2500")
        cartera = FacturaService.obtener_cartera_clientes()
        assert len(cartera) == 1
        assert cartera[0]["cliente_nombre"] == "Deudor SA"
        assert cartera[0]["saldo_pendiente"] == 2500.0

    def test_obtener_antiguedad_saldos(self):
        cliente_id = _crear_cliente(nombre="Atraso SA", nit="900000333")
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id, total="800")
        aging = FacturaService.obtener_antiguedad_saldos()
        assert len(aging) == 1
        assert aging[0]["saldo"] == 800.0
        assert "rango" in aging[0]


class TestExportarCartera:
    """FacturaService.exportar_cartera_excel — Excel export."""

    def test_exporta_cartera(self, tmp_path):
        cliente_id = _crear_cliente(nombre="Excel Export SA", nit="900000444")
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id, total="1500")
        ruta = tmp_path / "cartera.xlsx"
        ok, msg = FacturaService.exportar_cartera_excel(str(ruta))
        assert ok
        assert isinstance(msg, str)
        assert ruta.exists()
        assert ruta.stat().st_size > 0

    def test_exporta_cartera_vacia(self, tmp_path):
        _crear_cliente(nombre="Sin Deuda Export", nit="900000445")
        ruta = tmp_path / "cartera_vacia.xlsx"
        ok, msg = FacturaService.exportar_cartera_excel(str(ruta))
        assert ok
        assert isinstance(msg, str)
        assert ruta.exists()
