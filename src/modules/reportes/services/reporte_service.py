from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.pago_model import Pago
from src.modules.llantas.models.llanta_model import Llanta

import openpyxl
from openpyxl.styles import Font as ExcelFont, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HAS_OPENPYXL = True
from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.models.producto_model import Producto
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.services.llanta_service import UBICACIONES_DISPLAY


class ReporteService:
    """Report generation service with cross-module queries."""

    # =========================================================
    # Clientes Reports
    # =========================================================

    @staticmethod
    def clientes_por_ciudad() -> list[dict]:
        """Detailed client list with city, contact, tires-in-plant, and status."""
        with get_session() as session:
            sub_llantas = (
                session.query(
                    Llanta.cliente_id,
                    func.count(Llanta.id).label("cnt"),
                )
                .filter(
                    Llanta.estado.in_(["PENDIENTE", "APTA", "RECHAZADA", "REPARADA"]),
                )
                .group_by(Llanta.cliente_id)
                .subquery()
            )
            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.ciudad,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.activo,
                    func.coalesce(sub_llantas.c.cnt, 0),
                )
                .outerjoin(sub_llantas, Cliente.id == sub_llantas.c.cliente_id)
                .order_by(Cliente.ciudad, Cliente.nombre)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "ciudad": r[1] or "",
                    "contacto": r[2] or r[3] or "",
                    "nit": r[4] or "",
                    "activo": bool(r[5]),
                    "llantas_planta": r[6],
                }
                for r in results
            ]

    @staticmethod
    def clientes_activos_vs_inactivos(
        filtro: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Detailed client list with status and last-invoice date.

        Args:
            filtro: "ACTIVO", "INACTIVO", or None for all.
            fecha_desde: filter by last invoice ≥ this date.
            fecha_hasta: filter by last invoice ≤ this date.
        """
        with get_session() as session:
            from sqlalchemy import func as f

            q = session.query(
                Cliente.nombre,
                Cliente.telefono,
                Cliente.celular,
                Cliente.nit,
                Cliente.id,
                Cliente.activo,
                f.max(Factura.fecha_emision).label("ultima_vez"),
            ).outerjoin(Factura, Cliente.id == Factura.cliente_id)

            if filtro == "ACTIVO":
                q = q.filter(Cliente.activo.is_(True))
            elif filtro == "INACTIVO":
                q = q.filter(Cliente.activo.is_(False))

            results = (
                q.group_by(Cliente.id)
                .order_by(Cliente.nombre)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "contacto": r[1] or r[2] or "",
                    "nit": r[3] or "",
                    "id": r[4],
                    "activo": bool(r[5]),
                    "ultima_vez": (
                        r[6].strftime("%Y-%m-%d") if r[6] else "—"
                    ),
                }
                for r in results
            ]

    @staticmethod
    def clientes_con_mayor_saldo(
        limite: int = 10,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clients with highest pending balance, with optional date filter."""
        with get_session() as session:
            # Latest invoice with pending balance per client
            from sqlalchemy import desc

            sub_fact = (
                session.query(
                    Factura.cliente_id,
                    Factura.fecha_emision,
                    func.row_number()
                    .over(
                        partition_by=Factura.cliente_id,
                        order_by=desc(Factura.fecha_emision),
                    )
                    .label("rn"),
                )
                .filter(Factura.saldo > 0)
                .subquery()
            )

            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.saldo,
                    sub_fact.c.fecha_emision,
                )
                .outerjoin(
                    sub_fact,
                    (Cliente.id == sub_fact.c.cliente_id) & (sub_fact.c.rn == 1),
                )
                .filter(Cliente.saldo > 0)
            )

            if fecha_desde:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) >= func.date(fecha_desde),
                )
            if fecha_hasta:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) <= func.date(fecha_hasta),
                )

            results = (
                q.order_by(Cliente.saldo.desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "contacto": r[1] or r[2] or "",
                    "nit": r[3] or "",
                    "saldo": float(r[4] or 0),
                    "fecha_saldo": (
                        r[5].strftime("%Y-%m-%d") if r[5] else "—"
                    ),
                }
                for r in results
            ]

    @staticmethod
    def clientes_con_mayor_saldo_detalle(
        limite: int = 20,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clients with highest pending balance, with N° Cliente and date filter."""
        with get_session() as session:
            from sqlalchemy import desc

            sub_fact = (
                session.query(
                    Factura.cliente_id,
                    Factura.fecha_emision,
                    func.row_number()
                    .over(
                        partition_by=Factura.cliente_id,
                        order_by=desc(Factura.fecha_emision),
                    )
                    .label("rn"),
                )
                .filter(Factura.saldo > 0)
                .subquery()
            )

            q = (
                session.query(
                    Cliente.id,
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.saldo,
                    sub_fact.c.fecha_emision,
                )
                .outerjoin(
                    sub_fact,
                    (Cliente.id == sub_fact.c.cliente_id) & (sub_fact.c.rn == 1),
                )
                .filter(Cliente.saldo > 0)
            )

            if fecha_desde:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) >= func.date(fecha_desde),
                )
            if fecha_hasta:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) <= func.date(fecha_hasta),
                )

            results = (
                q.order_by(Cliente.saldo.desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "id": r[0],
                    "nombre": r[1],
                    "contacto": r[2] or r[3] or "",
                    "nit": r[4] or "",
                    "saldo": float(r[5] or 0),
                    "fecha_saldo": (
                        r[6].strftime("%Y-%m-%d") if r[6] else "—"
                    ),
                }
                for r in results
            ]

    # =========================================================
    # Llantas Reports
    # =========================================================

    # =========================================================
    # Unified Tire Report (replaces tabs 1-5)
    # =========================================================

    @staticmethod
    def reporte_llantas(
        cliente_id: int | None = None,
        estado: str | None = None,
        ubicacion: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        busqueda: str | None = None,
        solo_planta: bool = False,
    ) -> dict:
        """Unified tire report with combinable filters.
        
        Returns rows + KPIs computed on the filtered set.
        """
        from datetime import datetime as dt
        from sqlalchemy import desc

        ESTADOS_EN_PLANTA = ("PENDIENTE", "APTA", "RECHAZADA", "REPARADA")

        with get_session() as session:
            # ── Latest location per tire ──
            latest_ubicacion = (
                session.query(
                    UbicacionLlanta.llanta_id,
                    UbicacionLlanta.ubicacion,
                    func.row_number()
                    .over(
                        partition_by=UbicacionLlanta.llanta_id,
                        order_by=desc(UbicacionLlanta.fecha),
                    )
                    .label("rn"),
                )
                .subquery()
            )

            # ── Base query ──
            q = session.query(
                Llanta,
                latest_ubicacion.c.ubicacion,
                Cliente.nombre,
                Cliente.nit,
            ).outerjoin(Cliente, Llanta.cliente_id == Cliente.id).outerjoin(
                latest_ubicacion,
                (Llanta.id == latest_ubicacion.c.llanta_id)
                & (latest_ubicacion.c.rn == 1),
            )

            # ── Dynamic filters ──
            if cliente_id is not None:
                q = q.filter(Llanta.cliente_id == cliente_id)
            if estado:
                q = q.filter(Llanta.estado == estado)
            if ubicacion:
                q = q.filter(latest_ubicacion.c.ubicacion == ubicacion)
            if fecha_desde is not None:
                q = q.filter(Llanta.fecha_ingreso >= fecha_desde)
            if fecha_hasta is not None:
                q = q.filter(Llanta.fecha_ingreso <= fecha_hasta)
            if solo_planta:
                q = q.filter(Llanta.estado.in_(ESTADOS_EN_PLANTA))
            if busqueda:
                pattern = f"%{busqueda}%"
                q = q.filter(
                    Llanta.tiquete.ilike(pattern)
                    | Llanta.marca.ilike(pattern)
                    | Llanta.dimension.ilike(pattern)
                )

            results = q.order_by(Llanta.fecha_ingreso.desc()).all()

            # ── Build rows + KPIs ──
            now = dt.now()
            rows = []
            total_costo = 0.0
            total_precio = 0.0
            con_precio = 0
            sin_precio = 0
            en_planta = 0
            mas_30d = 0

            for l, ubic, cnombre, cnit in results:
                costo = float(l.costo_produccion or 0)
                precio = float(l.precio_venta or 0)
                utilidad = precio - costo
                if costo > 0 and precio > 0:
                    con_precio += 1
                    margen = round((utilidad / precio) * 100, 1)
                else:
                    sin_precio += 1
                    margen = None

                total_costo += costo
                total_precio += precio

                dias = 0
                if l.fecha_ingreso:
                    dias = (now - l.fecha_ingreso).days

                is_planta = l.estado in ESTADOS_EN_PLANTA if l.estado else False
                if is_planta:
                    en_planta += 1
                if is_planta and dias > 30:
                    mas_30d += 1

                ubic_display = (
                    UBICACIONES_DISPLAY.get(ubic, ubic)
                    if ubic else "—"
                )

                rows.append({
                    "id": l.id,
                    "tiquete": l.tiquete or "",
                    "cliente": cnombre or "—",
                    "cliente_id": l.cliente_id or 0,
                    "nit": cnit or "—",
                    "marca": l.marca or "",
                    "dimension": l.dimension_obj.display if l.dimension_obj else (l.dimension or ""),
                    "estado": l.estado or "",
                    "ubicacion": ubic_display,
                    "fecha_ingreso": (
                        l.fecha_ingreso.strftime("%Y-%m-%d")
                        if l.fecha_ingreso else "—"
                    ),
                    "dias_planta": dias,
                    "costo": round(costo, 2),
                    "precio": round(precio, 2) if precio > 0 else 0,
                    "utilidad": round(utilidad, 2),
                    "margen_pct": margen,
                })

            total_llantas = len(rows)
            return {
                "rows": rows,
                "kpis": {
                    "total": total_llantas,
                    "en_planta": en_planta,
                    "valor_inventario": round(total_costo, 2),
                    "mas_30d": mas_30d,
                    "utilidad_potencial": round(total_precio - total_costo, 2),
                    "con_precio": con_precio,
                    "sin_precio": sin_precio,
                },
            }

    # ── Export utility ──────────────────────────────────────────

    @staticmethod
    def exportar_excel(
        filename: str,
        headers: list[str],
        rows: list[list[str]],
    ) -> bool:
        """Write a table to an Excel file. Returns True on success."""
        if not HAS_OPENPYXL:
            return False
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte"

            hdr_font = ExcelFont(bold=True, color="FFFFFF")
            hdr_fill = PatternFill(
                start_color="2c3e50", end_color="2c3e50", fill_type="solid",
            )
            for ci, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=ci, value=h)
                cell.font = hdr_font
                cell.fill = hdr_fill
                cell.alignment = Alignment(horizontal="center")

            for ri, row in enumerate(rows, 2):
                for ci, val in enumerate(row, 1):
                    ws.cell(row=ri, column=ci, value=val)

            # Auto-fit column widths (capped)
            for col_idx in range(1, len(headers) + 1):
                max_len = len(str(headers[col_idx - 1]))
                for row_idx in range(2, len(rows) + 2):
                    cell_val = ws.cell(row=row_idx, column=col_idx).value
                    if cell_val:
                        max_len = max(max_len, len(str(cell_val)))
                ws.column_dimensions[
                    get_column_letter(col_idx)
                ].width = min(max_len + 3, 50)

            wb.save(filename)
            return True
        except Exception:
            return False

    @staticmethod
    # =========================================================
    # Finanzas Reports
    # =========================================================

    @staticmethod
    def facturas_detalle_por_mes(
        anio: int, mes: int | None = None,
    ) -> list[dict]:
        """Per-invoice detail for a given year/month."""
        with get_session() as session:
            q = session.query(
                Factura.id,
                Factura.numero,
                Factura.cliente_id,
                Cliente.nombre,
                Cliente.nit,
                Factura.total,
                Factura.saldo,
                Factura.estado,
                Factura.fecha_emision,
            ).join(Cliente, Factura.cliente_id == Cliente.id)

            if mes is not None:
                q = q.filter(
                    func.strftime("%Y-%m", Factura.fecha_emision) == f"{anio}-{mes:02d}"
                )
            else:
                q = q.filter(
                    func.strftime("%Y", Factura.fecha_emision) == str(anio)
                )

            facturas = q.order_by(Factura.fecha_emision.desc()).all()

            result = []
            for row in facturas:
                fid = row[0]
                num = row[1]
                result.append({
                    "id": int(fid or 0),
                    "cliente_id": int(row[2] or 0),
                    "cliente": row[3] or "—",
                    "nit": row[4] or "—",
                    "valor": float(row[5] or 0),
                    "saldo": float(row[6] or 0),
                    "estado": row[7] or "SIN ESTADO",
                    "fecha": row[8].strftime("%Y-%m-%d") if row[8] else "—",
                    "factura": f"#{num}" if num else f"ID {fid}",
                })
            return result

    @staticmethod
    def facturas_por_estado_detalle(estado: str | None = None) -> list[dict]:
        """Per-invoice list grouped by estado with cliente, total, fecha."""
        with get_session() as session:
            q = session.query(
                Factura.estado,
                Factura.id,
                Factura.cliente_id,
                Cliente.nombre,
                Cliente.nit,
                Factura.total,
                Factura.saldo,
                Factura.fecha_emision,
            ).join(Cliente, Factura.cliente_id == Cliente.id)
            if estado:
                q = q.filter(Factura.estado == estado)
            results = q.order_by(Factura.estado, Factura.fecha_emision.desc()).all()
            return [
                {
                    "id": int(r[1] or 0),
                    "cliente_id": int(r[2] or 0),
                    "cliente": r[3] or "—",
                    "nit": r[4] or "—",
                    "valor": float(r[5] or 0),
                    "saldo": float(r[6] or 0),
                    "fecha": r[7].strftime("%Y-%m-%d") if r[7] else "—",
                    "estado": r[0] or "SIN ESTADO",
                }
                for r in results
            ]

    # =========================================================
    # Detalle Financiero de Llantas
    # =========================================================

    @staticmethod
    def detalle_financiero_llantas() -> list[dict]:
        """Detailed tire financial report with status, location, client."""
        from sqlalchemy import desc

        with get_session() as session:
            # Subquery: latest location per tire
            latest_ubicacion = (
                session.query(
                    UbicacionLlanta.llanta_id,
                    UbicacionLlanta.ubicacion,
                    func.row_number()
                    .over(
                        partition_by=UbicacionLlanta.llanta_id,
                        order_by=desc(UbicacionLlanta.fecha),
                    )
                    .label("rn"),
                )
                .subquery()
            )

            llantas = (
                session.query(
                    Llanta,
                    latest_ubicacion.c.ubicacion,
                    Cliente.nombre,
                    Cliente.nit,
                )
                .outerjoin(Cliente, Llanta.cliente_id == Cliente.id)
                .outerjoin(
                    latest_ubicacion,
                    (Llanta.id == latest_ubicacion.c.llanta_id)
                    & (latest_ubicacion.c.rn == 1),
                )
                .order_by(Llanta.id.desc())
                .all()
            )

            result = []
            for l, ubicacion, cliente_nombre, cliente_nit in llantas:
                result.append(
                    {
                        "id": l.id,
                        "tiquete": l.tiquete or "",
                        "marca": l.marca or "",
                        "dimension": l.dimension_obj.display if l.dimension_obj else (l.dimension or ""),
                        "estado": l.estado or "",
                        "ubicacion": ubicacion or "—",
                        "cliente": cliente_nombre or "Sin cliente",
                        "nit": cliente_nit or "",
                        "costo_produccion": l.costo_produccion or 0,
                        "precio_venta": l.precio_venta or 0,
                    }
                )
            return result

    # =========================================================
    # Inventario Reports
    # =========================================================

    @staticmethod
    def inventario_por_categoria() -> list[dict]:
        """Per-product inventory with category, name, code, stock, value."""
        with get_session() as session:
            results = (
                session.query(
                    Producto.categoria,
                    Producto.nombre,
                    Producto.sku,
                    Producto.stock,
                    Producto.stock * Producto.costo_unitario,
                )
                .filter(Producto.activo.is_(True))
                .order_by(Producto.categoria, Producto.nombre)
                .all()
            )
            return [
                {
                    "categoria": r[0] or "SIN CATEGORIA",
                    "producto": r[1],
                    "codigo": r[2] or "",
                    "stock": float(r[3] or 0),
                    "valor": float(r[4] or 0),
                }
                for r in results
            ]

    @staticmethod
    def movimientos_por_tipo() -> list[dict]:
        """Movements with consecutive row number for each report."""
        with get_session() as session:
            results = (
                session.query(
                    MovimientoInventario.tipo,
                    func.count(MovimientoInventario.id),
                    func.sum(MovimientoInventario.cantidad),
                )
                .group_by(MovimientoInventario.tipo)
                .order_by(MovimientoInventario.tipo)
                .all()
            )
            return [
                {
                    "consecutivo": i + 1,
                    "tipo": r[0] or "OTRO",
                    "cantidad": r[1],
                    "total_unidades": float(r[2] or 0),
                }
                for i, r in enumerate(results)
            ]

    @staticmethod
    def productos_stock_bajo(limite: int = 10) -> list[dict]:
        with get_session() as session:
            productos = (
                session.query(Producto)
                .filter(
                    Producto.activo.is_(True),
                    Producto.stock < 10,
                )
                .order_by(Producto.stock.asc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": p.nombre,
                    "sku": p.sku,
                    "stock": float(p.stock or 0),
                }
                for p in productos
            ]

    # =========================================================
    # Dashboard Resumen
    # =========================================================

    @staticmethod
    def obtener_resumen_completo() -> dict:
        """Get a complete summary for the dashboard report."""
        with get_session() as session:
            total_clientes = session.query(Cliente).count()
            clientes_activos = session.query(Cliente).filter(Cliente.activo.is_(True)).count()
            clientes_inactivos = session.query(Cliente).filter(Cliente.activo.is_(False)).count()
            llantas_planta = session.query(Llanta).filter(
                Llanta.estado.in_(["PENDIENTE", "APTA", "RECHAZADA", "REPARADA"]),
            ).count()
            total_llantas = session.query(Llanta).count()
            total_facturas = session.query(Factura).count()
            facturas_pendientes = session.query(Factura).filter(Factura.saldo > 0).count()
            total_productos = (
                session.query(Producto)
                .filter(Producto.activo.is_(True))
                .count()
            )
            productos_stock_bajo = session.query(Producto).filter(
                Producto.activo.is_(True), Producto.stock < 10,
            ).count()
            total_pagos = session.query(Pago).count()
            total_movs = (
                session.query(MovimientoInventario).count()
            )

            facturacion_total = (
                session.query(
                    func.coalesce(func.sum(Factura.total), 0)
                )
                .filter(
                    func.strftime("%Y", Factura.fecha_emision)
                    == str(datetime.now().year)
                )
                .scalar()
            )

            valor_inventario = (
                session.query(
                    func.coalesce(
                        func.sum(
                            Producto.stock * Producto.costo_unitario
                        ),
                        0,
                    )
                )
                .filter(Producto.activo.is_(True))
                .scalar()
            )

        return {
            "total_clientes": total_clientes,
            "clientes_activos": clientes_activos,
            "clientes_inactivos": clientes_inactivos,
            "total_llantas": total_llantas,
            "llantas_en_planta": llantas_planta,
            "total_facturas": total_facturas,
            "facturas_pendientes": facturas_pendientes,
            "total_productos": total_productos,
            "productos_stock_bajo": productos_stock_bajo,
            "total_pagos": total_pagos,
            "total_movimientos": total_movs,
            "facturacion_anual": float(facturacion_total),
            "valor_inventario": float(valor_inventario),
        }

    # =========================================================
    # Movimientos en Planta
    # =========================================================

    # =========================================================
    # Indicadores Administrativos
    # =========================================================

    @staticmethod
    def indicadores_llantas() -> dict:
        """Indicadores financieros de llantas en planta.

        Returns:
            dict with:
                - resumen: {valor_inventario_planta, total_llantas_planta,
                            promedio_utilidad_bruta, total_utilidad_potencial,
                            llantas_con_precio, llantas_sin_precio}
                - detalle: list of per-tire dicts with utilidad and margen %
        """
        from sqlalchemy import desc

        ESTADOS_EN_PLANTA = ("PENDIENTE", "APTA", "RECHAZADA", "REPARADA")

        with get_session() as session:
            # ── Latest location per tire ──
            latest_ubicacion = (
                session.query(
                    UbicacionLlanta.llanta_id,
                    UbicacionLlanta.ubicacion,
                    func.row_number()
                    .over(
                        partition_by=UbicacionLlanta.llanta_id,
                        order_by=desc(UbicacionLlanta.fecha),
                    )
                    .label("rn"),
                )
                .subquery()
            )

            # ── Tires in plant ──
            llantas = (
                session.query(
                    Llanta,
                    latest_ubicacion.c.ubicacion,
                    Cliente.nombre,
                )
                .outerjoin(Cliente, Llanta.cliente_id == Cliente.id)
                .outerjoin(
                    latest_ubicacion,
                    (Llanta.id == latest_ubicacion.c.llanta_id)
                    & (latest_ubicacion.c.rn == 1),
                )
                .filter(Llanta.estado.in_(ESTADOS_EN_PLANTA))
                .order_by(Llanta.id.desc())
                .all()
            )

            # ── Compute KPIs ──
            total_costo = 0.0
            total_precio = 0.0
            llantas_con_precio = 0
            llantas_sin_precio = 0

            detalle = []
            for l, ubicacion, cliente_nombre in llantas:
                costo = float(l.costo_produccion or 0)
                precio = float(l.precio_venta or 0)
                utilidad = precio - costo

                if costo > 0 and precio > 0:
                    llantas_con_precio += 1
                    margen = round((utilidad / precio) * 100, 1)
                else:
                    llantas_sin_precio += 1
                    margen = None

                total_costo += costo
                total_precio += precio

                detalle.append({
                    "tiquete": l.tiquete or "",
                    "cliente": cliente_nombre or "Sin cliente",
                    "estado": l.estado or "",
                    "ubicacion": (
                        UBICACIONES_DISPLAY.get(ubicacion, ubicacion)
                        if ubicacion else "—"
                    ),
                    "costo": costo,
                    "precio": precio,
                    "utilidad": round(utilidad, 2),
                    "margen_pct": margen,
                })

            total_llantas = len(llantas)
            promedio_utilidad = (
                round(total_precio - total_costo, 2)
            )

            resumen = {
                "valor_inventario_planta": round(total_costo, 2),
                "total_llantas_planta": total_llantas,
                "promedio_utilidad_bruta": (
                    round((total_precio - total_costo) / total_llantas, 2)
                    if total_llantas > 0 else 0
                ),
                "total_utilidad_potencial": round(total_precio - total_costo, 2),
                "llantas_con_precio": llantas_con_precio,
                "llantas_sin_precio": llantas_sin_precio,
            }

            # ── Group by estado (only plant states) ──
            por_estado_rows = (
                session.query(
                    Llanta.estado,
                    func.count(Llanta.id),
                    func.coalesce(func.sum(Llanta.costo_produccion), 0),
                )
                .filter(Llanta.estado.in_(ESTADOS_EN_PLANTA))
                .group_by(Llanta.estado)
                .order_by(Llanta.estado)
                .all()
            )
            por_estado = [
                {
                    "estado": r[0] or "SIN ESTADO",
                    "cantidad": r[1],
                    "valor": float(r[2] or 0),
                }
                for r in por_estado_rows
            ]

            # ── Top clients by tire volume ──
            top_clientes_rows = (
                session.query(
                    Cliente.nombre,
                    func.count(Llanta.id),
                )
                .join(Llanta, Cliente.id == Llanta.cliente_id)
                .group_by(Cliente.id)
                .order_by(func.count(Llanta.id).desc())
                .limit(10)
                .all()
            )
            top_clientes = [
                {"cliente": r[0] or "—", "cantidad": r[1]}
                for r in top_clientes_rows
            ]

            return {
                "resumen": resumen,
                "detalle": detalle,
                "por_estado": por_estado,
                "top_clientes": top_clientes,
            }

    @staticmethod
    def indicador_reprocesadas() -> dict:
        """Indicador de llantas reprocesadas del mes.

        Una llanta se considera REPROCESADA cuando tiene 2+ registros con
        estado APTA en su historial (volvió a producción tras una
        inspección final). Se calcula sobre llantas con actividad en el
        mes y se compara contra el total de llantas REENCAUCHADAS.

        Returns:
            dict with:
                - cantidad: llantas reprocesadas en el mes
                - total_reencauchadas: llantas reencauchadas en el mes
                - porcentaje: % reprocesadas / reencauchadas
                - detalle: lista de llantas reprocesadas con su info
        """
        from datetime import datetime as dt
        from src.modules.llantas.models.estado_llanta_model import EstadoLlanta

        now = dt.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        with get_session() as session:
            # ── Llantas con 2+ APTA en su historial ──
            reprocesadas_ids = [
                r[0]
                for r in (
                    session.query(EstadoLlanta.llanta_id)
                    .filter(EstadoLlanta.estado == "APTA")
                    .group_by(EstadoLlanta.llanta_id)
                    .having(func.count(EstadoLlanta.id) > 1)
                    .all()
                )
            ]

            # ── Detalle de las reprocesadas (con actividad en el mes) ──
            detalle = []
            if reprocesadas_ids:
                reprocesadas_rows = (
                    session.query(
                        Llanta,
                        Cliente.nombre,
                    )
                    .outerjoin(Cliente, Llanta.cliente_id == Cliente.id)
                    .filter(Llanta.id.in_(reprocesadas_ids))
                    .all()
                )
                for l, cnombre in reprocesadas_rows:
                    ultimo_apta = (
                        session.query(EstadoLlanta.fecha)
                        .filter(
                            EstadoLlanta.llanta_id == l.id,
                            EstadoLlanta.estado == "APTA",
                        )
                        .order_by(EstadoLlanta.fecha.desc())
                        .first()
                    )
                    fecha = ultimo_apta[0] if ultimo_apta else None
                    if fecha is not None and fecha >= inicio_mes:
                        detalle.append({
                            "tiquete": l.tiquete or "",
                            "cliente": cnombre or "Sin cliente",
                            "marca": l.marca or "",
                            "dimension": l.dimension_obj.display if l.dimension_obj else (l.dimension or ""),
                            "fecha_reproceso": (
                                fecha.strftime("%Y-%m-%d") if fecha else "—"
                            ),
                            "estado": l.estado or "",
                        })

            # ── Total REENCAUCHADAS en el mes ──
            total_reencauchadas = (
                session.query(EstadoLlanta.llanta_id)
                .filter(
                    EstadoLlanta.estado == "REENCAUCHADA",
                    EstadoLlanta.fecha >= inicio_mes,
                )
                .distinct()
                .count()
            )

            cantidad = len(detalle)
            porcentaje = (
                round((cantidad / total_reencauchadas) * 100, 1)
                if total_reencauchadas > 0 else 0
            )

            return {
                "cantidad": cantidad,
                "total_reencauchadas": total_reencauchadas,
                "porcentaje": porcentaje,
                "detalle": detalle,
            }
