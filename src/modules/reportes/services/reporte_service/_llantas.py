"""Reportes de llantas — inclusivamente el reporte unificado de llantas."""

from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_llanta_model import FacturaLlanta
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service._core import formatear_tiquete
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.services.llanta_service import (
    ESTADOS_EN_PLANTA,
    UBICACIONES_DISPLAY,
)


class _LlantasReports:
    """Reportes del dominio Llantas."""

    @staticmethod
    def reporte_llantas(
        cliente_id: int | None = None,
        estado: str | None = None,
        ubicacion: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        busqueda: str | None = None,
        solo_planta: bool = False,
        diseno_id: int | None = None,
        dimension_id: int | None = None,
        limite: int | None = None,
        offset: int = 0,
    ) -> dict:
        """Unified tire report with combinable filters.

        Los KPIs se calculan con SQL agregado (rápido incluso con decenas
        de miles de llantas). Las filas detalladas aceptan paginación
        opcional (limite/offset).

        Returns rows + KPIs computed on the filtered set.
        """
        from datetime import datetime as dt
        from sqlalchemy import desc

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
                q = q.filter(
                    Llanta.estado.in_(ESTADOS_EN_PLANTA),
                    (latest_ubicacion.c.ubicacion.is_(None))
                    | (latest_ubicacion.c.ubicacion != "CLIENTE"),
                )
            if busqueda:
                pattern = f"%{busqueda}%"
                q = q.filter(
                    Llanta.tiquete.ilike(pattern)
                    | Llanta.marca.ilike(pattern)
                    | Llanta.dimension.ilike(pattern)
                )
            if diseno_id is not None:
                q = q.filter(Llanta.diseno_id == diseno_id)
            if dimension_id is not None:
                q = q.filter(Llanta.dimension_id == dimension_id)

            # ── KPIs y filas: costo/precio desde el catálogo (diseño+dimensión) ──
            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )

            idx = indice_precios(session)

            hace_30 = dt.now() - __import__("datetime").timedelta(days=30)

            # Cargar todas las llantas filtradas y resolver costo/precio del catálogo
            results = q.order_by(Llanta.fecha_ingreso.desc()).all()

            now = dt.now()
            rows = []
            total = 0
            en_planta = 0
            mas_30d = 0
            total_costo = 0.0
            total_precio = 0.0
            con_precio = 0

            for l, ubic, cnombre, cnit in results:
                total += 1
                costo, precio = costo_precio(l, idx)
                utilidad = precio - costo
                if costo > 0 and precio > 0:
                    con_precio += 1
                    margen = round((utilidad / precio) * 100, 1)
                else:
                    margen = None

                dias = 0
                if l.fecha_ingreso:
                    dias = (now - l.fecha_ingreso).days

                is_planta = (
                    (l.estado in ESTADOS_EN_PLANTA if l.estado else False)
                    and (ubic is None or ubic != "CLIENTE")
                )
                if is_planta:
                    en_planta += 1
                    if l.fecha_ingreso and l.fecha_ingreso <= hace_30:
                        mas_30d += 1

                total_costo += costo
                total_precio += precio

                ubic_display = (
                    UBICACIONES_DISPLAY.get(ubic, ubic)
                    if ubic else "—"
                )

                rows.append({
                    "id": l.id,
                    "tiquete": formatear_tiquete(l.tiquete),
                    "cliente": cnombre or "—",
                    "cliente_id": l.cliente_id or 0,
                    "nit": cnit or "—",
                    "marca": l.marca or "",
                    "dimension": (
                        l.dimension_obj.display
                        if l.dimension_obj else (l.dimension or "")
                    ),
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

            # Paginación de las filas mostradas
            if limite is not None:
                rows = rows[offset:offset + limite]

            sin_precio = total - con_precio

            return {
                "rows": rows,
                "kpis": {
                    "total": total,
                    "en_planta": en_planta,
                    "valor_inventario": round(total_costo, 2),
                    "mas_30d": mas_30d,
                    "utilidad_potencial": round(total_precio - total_costo, 2),
                    "con_precio": con_precio,
                    "sin_precio": sin_precio,
                },
            }

    # =========================================================
    # Detalle Financiero de Llantas
    # =========================================================

    @staticmethod
    def detalle_financiero_llantas() -> list[dict]:
        """Detailed tire financial report with status, location, client.

        Includes both re-treaded tires (from ``llantas``) and manual
        "llanta nueva" items billed on invoices (``factura_llantas`` rows
        with NULL ``llanta_id``). Each row carries a ``tipo`` field:
        "Reencauchada" or "Llanta nueva".
        """
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

            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )
            idx = indice_precios(session)

            result = []
            for l, ubicacion, cliente_nombre, cliente_nit in llantas:
                costo, precio = costo_precio(l, idx)
                result.append(
                    {
                        "tipo": "Reencauchada",
                        "id": l.id,
                        "tiquete": formatear_tiquete(l.tiquete),
                        "marca": l.marca or "",
                        "dimension": l.dimension_obj.display if l.dimension_obj else (l.dimension or ""),
                        "estado": l.estado or "",
                        "ubicacion": ubicacion or "—",
                        "cliente": cliente_nombre or "Sin cliente",
                        "nit": cliente_nit or "",
                        "costo_produccion": round(costo, 2),
                        "precio_venta": round(precio, 2),
                    }
                )

            # Llantas nuevas vendidas manualmente (sin registro en llantas).
            # Se unen a su factura (para cliente/NIT) y se excluyen ANULADAS.
            nuevas = (
                session.query(
                    FacturaLlanta.descripcion,
                    FacturaLlanta.precio_unitario,
                    Cliente.nombre,
                    Cliente.nit,
                )
                .join(Factura, FacturaLlanta.factura_id == Factura.id)
                .outerjoin(Cliente, Factura.cliente_id == Cliente.id)
                .filter(
                    FacturaLlanta.llanta_id.is_(None),
                    Factura.estado != "ANULADA",
                )
                .order_by(FacturaLlanta.id.desc())
                .all()
            )
            for descripcion, precio, cliente_nombre, cliente_nit in nuevas:
                result.append(
                    {
                        "tipo": "Llanta nueva",
                        "id": None,
                        "tiquete": descripcion or "—",
                        "marca": "",
                        "dimension": "",
                        "estado": "NUEVA",
                        "ubicacion": "FACTURADA",
                        "cliente": cliente_nombre or "Sin cliente",
                        "nit": cliente_nit or "",
                        "costo_produccion": 0,
                        "precio_venta": float(precio or 0),
                    }
                )
            return result

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
                .filter(
                    Llanta.estado.in_(ESTADOS_EN_PLANTA),
                    (latest_ubicacion.c.ubicacion.is_(None))
                    | (latest_ubicacion.c.ubicacion != "CLIENTE"),
                )
                .order_by(Llanta.id.desc())
                .all()
            )

            # ── Compute KPIs (costo/precio desde el catálogo) ──
            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )
            idx = indice_precios(session)

            total_costo = 0.0
            total_precio = 0.0
            llantas_con_precio = 0
            llantas_sin_precio = 0
            por_estado_acum: dict[str, dict] = {}

            detalle = []
            for l, ubicacion, cliente_nombre in llantas:
                costo, precio = costo_precio(l, idx)
                utilidad = precio - costo

                if costo > 0 and precio > 0:
                    llantas_con_precio += 1
                    margen = round((utilidad / precio) * 100, 1)
                else:
                    llantas_sin_precio += 1
                    margen = None

                total_costo += costo
                total_precio += precio

                estado_key = l.estado or "SIN ESTADO"
                acc = por_estado_acum.setdefault(estado_key, {"cantidad": 0, "valor": 0.0})
                acc["cantidad"] += 1
                acc["valor"] += costo

                detalle.append({
                    "tiquete": formatear_tiquete(l.tiquete),
                    "cliente": cliente_nombre or "Sin cliente",
                    "estado": l.estado or "",
                    "ubicacion": (
                        UBICACIONES_DISPLAY.get(ubicacion, ubicacion)
                        if ubicacion else "—"
                    ),
                    "costo": round(costo, 2),
                    "precio": round(precio, 2),
                    "utilidad": round(utilidad, 2),
                    "margen_pct": margen,
                })

            total_llantas = len(llantas)
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

            por_estado = [
                {
                    "estado": estado,
                    "cantidad": acc["cantidad"],
                    "valor": round(acc["valor"], 2),
                }
                for estado, acc in sorted(por_estado_acum.items())
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
                            "tiquete": formatear_tiquete(l.tiquete),
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