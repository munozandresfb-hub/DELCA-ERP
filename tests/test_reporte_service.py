"""ReporteService unit tests — regression guards for key bugs + core reports.

Uses the ``service_db`` fixture so every ``get_session()`` call inside the
service hits an isolated temporary database.

Regression targets:
  - clientes_con_mayor_saldo_detalle() MUST return "id" per row
    (the view reads row["id"]; the non-detalle variant omits it).
  - facturas_por_estado_detalle() MUST return "valor" per row
    (was "total" → KeyError regression fixed in reportes_view).
"""

from decimal import Decimal

from datetime import datetime, timedelta

import pytest

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.services.llanta_service import LlantaService
from src.modules.reportes.services.reporte_service import ReporteService


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


def _crear_cliente(nombre: str = "Reporte Cliente", nit: str = "901234567") -> int:
    with get_session() as session:
        cliente = Cliente(nombre=nombre, nit=nit)
        session.add(cliente)
        session.flush()
        return cliente.id


def _crear_llanta(tiquete: str = "RPT-TQ-001") -> int:
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


def _crear_factura_nueva(cliente_id: int, total: str = "1500") -> int:
    ok, res = FacturaService.crear(
        cliente_id=cliente_id,
        total=Decimal(total),
        items=[
            {"descripcion": "Goodyear 295/80 R22.5 nueva", "precio_unitario": Decimal(total)}
        ],
    )
    assert ok, f"crear factura con llanta nueva falló: {res}"
    return res.id


def _crear_llanta_cliente(
    cliente_id: int,
    tiquete: str,
    fecha_ingreso: datetime,
    estado: str = "REENCAUCHADA",
    fecha_salida: datetime | None = None,
) -> int:
    """Crea una llanta con fecha de ingreso, estado final y salida al cliente."""
    ok, llanta = LlantaService.crear(
        tiquete=tiquete, cliente_id=cliente_id, fecha_ingreso=fecha_ingreso
    )
    assert ok, f"crear llanta falló: {llanta}"
    with get_session() as session:
        db_llanta = session.get(Llanta, llanta.id)
        db_llanta.estado = estado
        db_llanta.ubicacion_actual = "CLIENTE"
        session.add(db_llanta)
        session.flush()
        if fecha_salida is not None:
            salida = UbicacionLlanta(
                llanta_id=db_llanta.id,
                ubicacion="CLIENTE",
                fecha=fecha_salida,
            )
            session.add(salida)
    return llanta.id


def _crear_cliente_con_contacto(
    nombre: str = "Nuevo Prospecto", nit: str = "901234599", celular: str = "3001234567"
) -> int:
    with get_session() as session:
        cliente = Cliente(nombre=nombre, nit=nit, celular=celular)
        session.add(cliente)
        session.flush()
        return cliente.id


def _crear_cliente_sin_contacto(
    nombre: str = "Sin Contacto", nit: str = "901234598"
) -> int:
    with get_session() as session:
        cliente = Cliente(nombre=nombre, nit=nit)
        session.add(cliente)
        session.flush()
        return cliente.id


class TestMayorSaldoDetalle:
    """Regression: clientes_con_mayor_saldo_detalle must include 'id'."""

    def test_fila_incluye_id(self):
        cliente_id = _crear_cliente(nombre="Deudor Mayor", nit="901234568")
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id, total="5000")
        rows = ReporteService.clientes_con_mayor_saldo_detalle()
        assert len(rows) == 1
        row = rows[0]
        assert "id" in row
        assert row["id"] == cliente_id
        assert "nombre" in row
        assert "saldo" in row

    def test_sin_saldo_devuelve_vacio(self):
        _crear_cliente(nombre="Sin Deuda", nit="901234569")
        rows = ReporteService.clientes_con_mayor_saldo_detalle()
        assert rows == []

    def test_limite_respetado(self):
        for i in range(3):
            cid = _crear_cliente(nombre=f"Cliente {i}", nit=f"90123457{i}")
            lid = _crear_llanta(tiquete=f"RPT-L{i}")
            _crear_factura(cid, lid, total="1000")
        rows = ReporteService.clientes_con_mayor_saldo_detalle(limite=2)
        assert len(rows) == 2


class TestFacturasPorEstadoDetalle:
    """Regression: facturas_por_estado_detalle must use 'valor', not 'total'."""

    def test_fila_incluye_valor(self):
        cliente_id = _crear_cliente(nombre="Facturado SA", nit="901234570")
        llanta_id = _crear_llanta()
        _crear_factura(cliente_id, llanta_id, total="2500")
        rows = ReporteService.facturas_por_estado_detalle()
        assert len(rows) == 1
        row = rows[0]
        assert "valor" in row
        assert "total" not in row
        assert row["valor"] == 2500.0
        assert row["estado"] == "PENDIENTE"

    def test_filtro_por_estado(self):
        cliente_id = _crear_cliente(nombre="Estados SA", nit="901234571")
        llanta_id = _crear_llanta()
        factura_id = _crear_factura(cliente_id, llanta_id, total="1000")
        FacturaService.anular(factura_id)
        pendientes = ReporteService.facturas_por_estado_detalle(estado="PENDIENTE")
        assert pendientes == []
        anuladas = ReporteService.facturas_por_estado_detalle(estado="ANULADA")
        assert len(anuladas) == 1
        assert anuladas[0]["estado"] == "ANULADA"

    def test_sin_facturas_devuelve_vacio(self):
        _crear_cliente(nombre="Sin Facturas", nit="901234572")
        assert ReporteService.facturas_por_estado_detalle() == []


class TestReportesLlantas:
    """ReporteService.reporte_llantas — unified tire report."""

    def test_rows_y_kpis(self):
        _crear_llanta(tiquete="RPT-UNI-1")
        _crear_llanta(tiquete="RPT-UNI-2")
        reporte = ReporteService.reporte_llantas()
        assert reporte["kpis"]["total"] == 2
        assert len(reporte["rows"]) == 2
        primera = reporte["rows"][0]
        assert "tiquete" in primera
        assert "estado" in primera
        assert "ubicacion" in primera

    def test_filtro_por_estado(self):
        llanta_id = _crear_llanta(tiquete="RPT-FILT-1")
        _crear_llanta(tiquete="RPT-FILT-2")
        LlantaService.cambiar_estado(llanta_id, "APTA")
        solo_apta = ReporteService.reporte_llantas(estado="APTA")
        assert solo_apta["kpis"]["total"] == 1
        assert solo_apta["rows"][0]["estado"] == "APTA"

    def test_filtro_busqueda(self):
        _crear_llanta(tiquete="RPT-BUSQ-777")
        _crear_llanta(tiquete="RPT-BUSQ-888")
        por_busqueda = ReporteService.reporte_llantas(busqueda="777")
        assert por_busqueda["kpis"]["total"] == 1


class TestResumenCompleto:
    """ReporteService.obtener_resumen_completo — dashboard summary."""

    def test_claves_presentes(self):
        _crear_cliente(nombre="Resumen SA", nit="901234573")
        resumen = ReporteService.obtener_resumen_completo()
        for clave in (
            "total_clientes",
            "total_llantas",
            "total_facturas",
            "total_productos",
            "facturacion_anual",
            "valor_inventario",
        ):
            assert clave in resumen, f"falta clave {clave}"
        assert resumen["total_clientes"] == 1


class TestExportarExcel:
    """ReporteService.exportar_excel — export utility."""

    def test_exporta_archivo(self, tmp_path):
        ruta = tmp_path / "reporte_test.xlsx"
        ok = ReporteService.exportar_excel(
            str(ruta),
            headers=["Columna A", "Columna B"],
            rows=[["v1", "v2"], ["v3", "v4"]],
        )
        assert ok
        assert ruta.exists()
        assert ruta.stat().st_size > 0


class TestDetalleFinancieroLlantas:
    """ReporteService.detalle_financiero_llantas — distingue Reencauchada vs Llanta nueva."""

    def test_reencauchada_incluye_tipo(self):
        cliente_id = _crear_cliente(nombre="Taller Reencauchado", nit="901234574")
        llanta_id = _crear_llanta(tiquete="RPT-DET-1")
        _crear_factura(cliente_id, llanta_id, total="1000")
        rows = ReporteService.detalle_financiero_llantas()
        assert len(rows) == 1
        assert rows[0]["tipo"] == "Reencauchada"
        assert rows[0]["id"] == llanta_id

    def test_llanta_nueva_incluye_descripcion(self):
        cliente_id = _crear_cliente(nombre="Comprador Nuevo", nit="901234575")
        _crear_factura_nueva(cliente_id, total="1500")
        rows = ReporteService.detalle_financiero_llantas()
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo"] == "Llanta nueva"
        assert row["id"] is None
        assert row["tiquete"] == "Goodyear 295/80 R22.5 nueva"
        assert row["precio_venta"] == 1500.0

    def test_mixto_reencauchada_y_nueva(self):
        cliente_id = _crear_cliente(nombre="Cliente Mixto", nit="901234576")
        llanta_id = _crear_llanta(tiquete="RPT-DET-2")
        _crear_factura(cliente_id, llanta_id, total="1000")
        _crear_factura_nueva(cliente_id, total="1500")
        rows = ReporteService.detalle_financiero_llantas()
        assert len(rows) == 2
        tipos = {r["tipo"] for r in rows}
        assert tipos == {"Reencauchada", "Llanta nueva"}

    def test_factura_anulada_excluye_llanta_nueva(self):
        cliente_id = _crear_cliente(nombre="Anulador SA", nit="901234577")
        factura_id = _crear_factura_nueva(cliente_id, total="1500")
        FacturaService.anular(factura_id)
        rows = ReporteService.detalle_financiero_llantas()
        assert rows == []


class TestClientesInactivos:
    """ReporteService.clientes_inactivos — reactivación comercial."""

    CORTE = datetime(2026, 9, 3)

    def test_inactivo_con_historial(self):
        cid = _crear_cliente(nombre="Inactivo Hist", nit="901234580")
        ingreso = self.CORTE - timedelta(days=400)
        _crear_llanta_cliente(
            cid, "RPT-INACT-1", ingreso, estado="REENCAUCHADA",
            fecha_salida=ingreso + timedelta(days=10),
        )
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert len(inactivos) == 1
        assert inactivos[0]["nombre"] == "Inactivo Hist"
        assert inactivos[0]["ultima_vez"] == (ingreso + timedelta(days=10)).strftime("%Y-%m-%d")
        assert inactivos[0]["dias_sin_actividad"] == 390
        assert inactivos[0]["rango_inactividad"] == "366-730 días (1-2 años)"

    def test_inactivo_excluye_reciente(self):
        cid = _crear_cliente(nombre="Reciente", nit="901234581")
        _crear_llanta_cliente(
            cid, "RPT-REC-1", self.CORTE - timedelta(days=100),
            fecha_salida=self.CORTE - timedelta(days=100),
        )
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert inactivos == []

    def test_inactivo_excluye_llanta_en_planta(self):
        cid = _crear_cliente(nombre="En Planta", nit="901234582")
        # Llanta vieja PERO aún en planta (ubicacion_actual PLANTA, no CLIENTE)
        ok, llanta = LlantaService.crear(
            tiquete="RPT-PL-1", cliente_id=cid,
            fecha_ingreso=self.CORTE - timedelta(days=400),
        )
        assert ok
        with get_session() as session:
            db_llanta = session.get(Llanta, llanta.id)
            db_llanta.estado = "REENCAUCHADA"
            db_llanta.ubicacion_actual = "PLANTA"
            session.add(db_llanta)
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert inactivos == []

    def test_inactivo_excluye_sin_historial(self):
        # Cliente sin llantas pero con contacto → NO es inactivo, es 1er venta
        _crear_cliente_con_contacto(nombre="Solo Prospecto", nit="901234583")
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert inactivos == []

    def test_primer_venta_con_contacto(self):
        _crear_cliente_con_contacto(nombre="Prospecto Con", nit="901234584")
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        pv = [r for r in rows if r["es_primer_venta"]]
        assert len(pv) == 1
        assert pv[0]["nombre"] == "Prospecto Con"
        assert pv[0]["dias_sin_actividad"] == "1er venta"
        assert pv[0]["rango_inactividad"] == "1096+ días (3+ años)"
        assert pv[0]["segmento_dimension"] == "—"
        assert pv[0]["llantas_aptas"] == 0

    def test_primer_venta_sin_contacto_excluido(self):
        # Sin historial Y sin contacto → NO aparece (permanece en BD)
        _crear_cliente_sin_contacto(nombre="Fantasma", nit="901234585")
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        nombres = {r["nombre"] for r in rows}
        assert "Fantasma" not in nombres

    def test_primer_venta_opcional(self):
        _crear_cliente_con_contacto(nombre="Prospecto Off", nit="901234586")
        rows = ReporteService.clientes_inactivos(
            fecha_corte=self.CORTE, incluir_primer_venta=False
        )
        assert all(not r["es_primer_venta"] for r in rows)

    def test_orden_desc(self):
        c1 = _crear_cliente(nombre="Inactivo Viejo", nit="901234587")
        c2 = _crear_cliente(nombre="Inactivo Nuevo", nit="901234588")
        _crear_llanta_cliente(
            c1, "RPT-ORD-1", self.CORTE - timedelta(days=500),
            fecha_salida=self.CORTE - timedelta(days=500),
        )
        _crear_llanta_cliente(
            c2, "RPT-ORD-2", self.CORTE - timedelta(days=350),
            fecha_salida=self.CORTE - timedelta(days=350),
        )
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert [r["nombre"] for r in inactivos] == ["Inactivo Nuevo", "Inactivo Viejo"]

    def test_llantas_aptas(self):
        cid = _crear_cliente(nombre="Con Aptas", nit="901234589")
        base = self.CORTE - timedelta(days=500)
        # 2 reencauchadas (aptas) + 1 rechazada (no apta)
        _crear_llanta_cliente(cid, "RPT-APT-1", base, estado="REENCAUCHADA",
                              fecha_salida=base + timedelta(days=5))
        _crear_llanta_cliente(cid, "RPT-APT-2", base, estado="REENCAUCHADA",
                              fecha_salida=base + timedelta(days=5))
        _crear_llanta_cliente(cid, "RPT-APT-3", base, estado="RECHAZADA",
                              fecha_salida=base + timedelta(days=5))
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert len(inactivos) == 1
        assert inactivos[0]["llantas_aptas"] == 2

    def test_segmento_dimension(self):
        cid = _crear_cliente(nombre="Con Dimension", nit="901234590")
        base = self.CORTE - timedelta(days=500)
        # Sin FK de dimensión: usa texto legacy llantas.dimension
        with get_session() as session:
            for i, dim in enumerate(["295/80 R22.5", "295/80 R22.5", "11.00-20", "295/80 R22.5"]):
                ok, llanta = LlantaService.crear(
                    tiquete=f"RPT-DIM-{i}", cliente_id=cid,
                    fecha_ingreso=base,
                )
                assert ok
                db_llanta = session.get(Llanta, llanta.id)
                db_llanta.dimension = dim
                db_llanta.estado = "REENCAUCHADA"
                db_llanta.ubicacion_actual = "CLIENTE"
                session.add(db_llanta)
            session.flush()
        rows = ReporteService.clientes_inactivos(fecha_corte=self.CORTE)
        inactivos = [r for r in rows if not r["es_primer_venta"]]
        assert len(inactivos) == 1
        assert inactivos[0]["segmento_dimension"] == "295/80 R22.5"
