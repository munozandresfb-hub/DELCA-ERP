"""Reportes de clientes — ReporteService para el dominio de clientes.

Contiene los reportes que consultan exclusivamente datos de clientes
(saldo, actividad, columnas por ciudad).
"""

from datetime import datetime, timedelta

from sqlalchemy import case, func, or_

from src.core.services.cliente_actividad import (
    es_activo as _es_activo,
    sub_llantas_en_planta as _sub_llantas_en_planta,
    sub_ultima_actividad as _sub_ultima_actividad,
)
from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta

# Rangos comerciales de inactividad (configurables): (min, max, label)
SEGMENTOS_RANGO = [
    (300, 365, "300-365 días (reciente)"),
    (366, 730, "366-730 días (1-2 años)"),
    (731, 1095, "731-1095 días (2-3 años)"),
    (1096, None, "1096+ días (3+ años)"),
]


class _ClientesReports:
    """Reportes del dominio Clientes."""

    @staticmethod
    def clientes_activos_vs_inactivos(
        filtro: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con estado Activo/Inactivo (definición operativa confirmada, opción B).

        Definición (evaluada con el fin del segmento [fecha_desde, fecha_hasta]):
          ACTIVO   = tiene ≥1 llanta en planta/producción (no entregada)
                     O tuvo actividad DESPUÉS del fin del segmento (última
                     actividad posterior a fecha_hasta — siguió trayendo).
          INACTIVO = sin llantas en planta/producción Y sin actividad posterior
                     al fin del segmento (última actividad ≤ fecha_hasta — dejó
                     de venir a más tardar al final del periodo) Y con historial
                     previo (alguna vez trajo llantas).

        Args:
            filtro: "ACTIVO", "INACTIVO", or None for all.
            fecha_desde: inicio del segmento de tiempo (delimita el periodo).
            fecha_hasta: fin del segmento — umbral de la actividad posterior.
        """
        with get_session() as session:
            sub_planta = _sub_llantas_en_planta(session)
            # Última actividad TOTAL (historial completo): la clasificación
            # evalúa si hubo actividad DESPUÉS del fin del segmento.
            sub_actividad = _sub_ultima_actividad(session)

            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    func.coalesce(sub_planta.c.cnt, 0),
                    sub_actividad.c.ultima_actividad,
                )
                .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
                .outerjoin(sub_actividad, Cliente.id == sub_actividad.c.cliente_id)
                .order_by(Cliente.nombre)
                .all()
            )

            filas: list[dict] = []
            for r in results:
                llantas_planta = r[5] or 0
                ultima_actividad = r[6]
                activo = _es_activo(llantas_planta, ultima_actividad, fecha_hasta)
                if filtro == "ACTIVO" and not activo:
                    continue
                if filtro == "INACTIVO":
                    # INACTIVO = sin llantas en planta/producción + sin actividad
                    # posterior al fin del segmento (última actividad ≤ hasta) +
                    # con historial previo (los clientes sin ningún movimiento
                    # nunca trajeron llantas — no son recuperables).
                    if activo or ultima_actividad is None:
                        continue
                filas.append(
                    {
                        "nombre": r[0],
                        "contacto": r[1] or r[2] or "",
                        "nit": r[3] or "",
                        "id": r[4],
                        "activo": activo,
                        "ultima_vez": (
                            ultima_actividad.strftime("%Y-%m-%d")
                            if ultima_actividad
                            else "—"
                        ),
                        "llantas_planta": llantas_planta,
                    }
                )
            return filas

    @staticmethod
    def _sub_saldo_por_cliente(session, fecha_desde, fecha_hasta):
        """Subquery: saldo pendiente REAL por cliente (suma de facturas).

        El saldo se calcula desde las facturas (estado != ANULADA, saldo > 0)
        — NO del campo legacy Cliente.saldo — y las fechas filtran DENTRO del
        subquery (evita que un join vacío elimine todos los clientes).
        """
        q = (
            session.query(
                Factura.cliente_id,
                Factura.saldo,
                Factura.fecha_emision,
            )
            .filter(
                Factura.saldo > 0,
                Factura.estado != "ANULADA",
                Factura.cliente_id.isnot(None),
            )
        )
        if fecha_desde:
            q = q.filter(Factura.fecha_emision >= fecha_desde)
        if fecha_hasta:
            q = q.filter(Factura.fecha_emision <= fecha_hasta)
        fact_sub = q.subquery()
        return (
            session.query(
                fact_sub.c.cliente_id,
                func.sum(fact_sub.c.saldo).label("saldo"),
                func.max(fact_sub.c.fecha_emision).label("ultima_factura"),
            )
            .group_by(fact_sub.c.cliente_id)
            .subquery()
        )

    @staticmethod
    def clientes_con_mayor_saldo(
        limite: int = 10,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con mayor saldo pendiente (calculado de facturas reales)."""
        with get_session() as session:
            sub_saldo = _ClientesReports._sub_saldo_por_cliente(
                session, fecha_desde, fecha_hasta
            )
            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    func.coalesce(sub_saldo.c.saldo, 0),
                    sub_saldo.c.ultima_factura,
                )
                .outerjoin(sub_saldo, Cliente.id == sub_saldo.c.cliente_id)
                .filter(func.coalesce(sub_saldo.c.saldo, 0) > 0)
                .order_by(func.coalesce(sub_saldo.c.saldo, 0).desc())
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
                for r in q
            ]

    @staticmethod
    def clientes_con_mayor_saldo_detalle(
        limite: int = 20,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con mayor saldo pendiente, con N° Cliente (facturas reales)."""
        with get_session() as session:
            sub_saldo = _ClientesReports._sub_saldo_por_cliente(
                session, fecha_desde, fecha_hasta
            )
            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    Cliente.email,
                    func.coalesce(sub_saldo.c.saldo, 0),
                    sub_saldo.c.ultima_factura,
                )
                .outerjoin(sub_saldo, Cliente.id == sub_saldo.c.cliente_id)
                .filter(func.coalesce(sub_saldo.c.saldo, 0) > 0)
                .order_by(func.coalesce(sub_saldo.c.saldo, 0).desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "contacto": r[1] or r[2] or "",
                    "nit": r[3] or "",
                    "id": r[4],
                    "email": r[5] or "",
                    "saldo": float(r[6] or 0),
                    "fecha_saldo": (
                        r[7].strftime("%Y-%m-%d") if r[7] else "—"
                    ),
                }
                for r in q
            ]

    # ── Clientes Inactivos (reactivación comercial) ─────────────────

    @staticmethod
    def _sub_ultima_actividad_comercial(session):
        """Subquery: última actividad REAL del cliente (entrada o salida de llantas).

        Entrada  = llantas.fecha_ingreso (trajo llantas a reencauchar)
        Salida   = ubicaciones_llanta.fecha donde ubicacion == 'CLIENTE' (retiró)
        Excluye cambios de estado, ubicaciones internas y facturas (trabajo interno).
        """
        entradas = (
            session.query(
                Llanta.cliente_id.label("cliente_id"),
                Llanta.fecha_ingreso.label("fecha"),
            )
            .filter(Llanta.fecha_ingreso.isnot(None), Llanta.cliente_id.isnot(None))
        )
        salidas = (
            session.query(
                Llanta.cliente_id.label("cliente_id"),
                UbicacionLlanta.fecha.label("fecha"),
            )
            .join(UbicacionLlanta, UbicacionLlanta.llanta_id == Llanta.id)
            .filter(
                UbicacionLlanta.ubicacion == "CLIENTE",
                UbicacionLlanta.fecha.isnot(None),
                Llanta.cliente_id.isnot(None),
            )
        )
        union = entradas.union_all(salidas).subquery()
        return (
            session.query(
                union.c.cliente_id.label("cliente_id"),
                func.max(union.c.fecha).label("ultima_actividad"),
            )
            .group_by(union.c.cliente_id)
            .subquery()
        )

    @staticmethod
    def _sub_llantas_aptas(session):
        """Subquery: cantidad de llantas APTAS por cliente.

        'Aptas' = llantas cuyo resultado fue útil (estado APTA en proceso,
        REENCAUCHADA o REPARADA ya terminadas) — excluye RECHAZADA. El estado
        'APTA' puro es transitorio en el flujo (PENDIENTE → APTA → terminada),
        por lo que contar solo 'APTA' dejaría el valor en 0 para casi todos.
        """
        return (
            session.query(
                Llanta.cliente_id.label("cliente_id"),
                func.sum(
                    case(
                        (Llanta.estado.in_(("APTA", "REENCAUCHADA", "REPARADA")), 1),
                        else_=0,
                    )
                ).label("aptas"),
            )
            .filter(Llanta.cliente_id.isnot(None))
            .group_by(Llanta.cliente_id)
            .subquery()
        )

    @staticmethod
    def _dimension_dominante(session) -> dict[int, str]:
        """Dimensión que más trajo cada cliente (moda).

        Usa dimensiones_llanta.display cuando hay FK; fallback a llantas.dimension
        (texto legacy) cuando dimension_id es NULL.
        """
        rows = (
            session.query(
                Llanta.cliente_id,
                func.coalesce(
                    DimensionLlanta.ancho, None
                ).label("ancho"),
                func.coalesce(DimensionLlanta.perfil, None).label("perfil"),
                func.coalesce(DimensionLlanta.rin, None).label("rin"),
                func.coalesce(DimensionLlanta.sufijo, "").label("sufijo"),
                Llanta.dimension.label("dim_texto"),
            )
            .outerjoin(DimensionLlanta, Llanta.dimension_id == DimensionLlanta.id)
            .filter(Llanta.cliente_id.isnot(None))
            .all()
        )

        def _display(ancho, perfil, rin, sufijo, dim_texto) -> str | None:
            if ancho is not None or perfil is not None or rin is not None:
                # Replica DimensionLlanta.display (ancho/perfil/rin/sufijo)
                s = sufijo or ""
                if rin is None:
                    if perfil is None:
                        return f"{_fmt(ancho)}{s}"
                    return f"{_fmt(ancho)}-{perfil}{s}"
                rin_str = (
                    f"{rin:.1f}" if rin != int(rin) else str(int(rin))
                )
                if perfil is None:
                    return f"{_fmt(ancho)} R{rin_str}{s}"
                return f"{_fmt(ancho)}/{perfil} R{rin_str}{s}"
            return dim_texto or None

        def _fmt(val) -> str:
            if val is None:
                return ""
            v = float(val)
            if v == int(v):
                return str(int(v))
            return f"{v:.2f}".rstrip("0").rstrip(".")

        # Moda por cliente: (cliente_id -> (conteo, display))
        conteos: dict[int, dict[str, int]] = {}
        for cliente_id, ancho, perfil, rin, sufijo, dim_texto in rows:
            if cliente_id is None:
                continue
            display = _display(ancho, perfil, rin, sufijo, dim_texto)
            if not display:
                continue
            por_cliente = conteos.setdefault(cliente_id, {})
            por_cliente[display] = por_cliente.get(display, 0) + 1

        moda: dict[int, str] = {}
        for cliente_id, conteo in conteos.items():
            moda[cliente_id] = max(conteo.items(), key=lambda kv: kv[1])[0]
        return moda

    @staticmethod
    def _segmento_para(
        dias: int, segmentos: list[tuple[int, int | None, str]]
    ) -> str:
        """Label del primer rango [min, max] que contiene `dias` (max None = sin tope)."""
        for lo, hi, label in segmentos:
            if dias >= lo and (hi is None or dias <= hi):
                return label
        return "—"

    @staticmethod
    def clientes_inactivos(
        dias_minimo: int = 300,
        fecha_corte: datetime | None = None,
        incluir_primer_venta: bool = True,
    ) -> list[dict]:
        """Clientes inactivos + candidatos 1er venta (reactivación comercial).

        INACTIVO  = con historial (alguna vez trajo llantas) + última actividad
                    (entrada/salida) anterior a `dias_minimo` días desde
                    `fecha_corte` + sin llantas en planta/producción.
                    Orden: última actividad DESC (más reciente → más antigua).
        PRIMER VENTA = sin historial de compra PERO con contacto
                    (celular/teléfono/email). Rango 3+ años, '1er venta' en
                    dias_sin_actividad. Los sin historial y sin contacto se
                    excluyen del reporte (permanecen en la BD).

        Returns:
            list[dict] con: nombre, contacto, nit, email, ciudad,
            llantas_aptas, segmento_dimension, ultima_vez, dias_sin_actividad,
            llantas_planta, es_primer_venta, rango_inactividad.
        """
        corte = fecha_corte or datetime.now()
        corte_limite = corte - timedelta(days=dias_minimo)
        filas: list[dict] = []

        with get_session() as session:
            sub_planta = _sub_llantas_en_planta(session)
            sub_actividad = _ClientesReports._sub_ultima_actividad_comercial(session)
            sub_aptas = _ClientesReports._sub_llantas_aptas(session)
            dim_moda = _ClientesReports._dimension_dominante(session)

            # ── INACTIVOS (con historial, sin actividad reciente, sin planta) ──
            results = (
                session.query(
                    Cliente.id,
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.email,
                    Cliente.ciudad,
                    func.coalesce(sub_aptas.c.aptas, 0),
                    func.coalesce(sub_planta.c.cnt, 0),
                    sub_actividad.c.ultima_actividad,
                )
                .join(sub_actividad, Cliente.id == sub_actividad.c.cliente_id)
                .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
                .outerjoin(sub_aptas, Cliente.id == sub_aptas.c.cliente_id)
                .filter(
                    sub_actividad.c.ultima_actividad < corte_limite,
                    func.coalesce(sub_planta.c.cnt, 0) == 0,
                )
                .order_by(sub_actividad.c.ultima_actividad.desc())
                .all()
            )

            for (cid, nombre, telefono, celular, nit, email, ciudad,
                 aptas, llantas_planta, ultima_actividad) in results:
                dias = (corte - ultima_actividad).days
                filas.append(
                    {
                        "nombre": nombre,
                        "contacto": telefono or celular or "",
                        "nit": nit or "",
                        "email": email or "",
                        "ciudad": ciudad or "",
                        "llantas_aptas": int(aptas or 0),
                        "segmento_dimension": dim_moda.get(cid, "—"),
                        "ultima_vez": ultima_actividad.strftime("%Y-%m-%d"),
                        "dias_sin_actividad": dias,
                        "llantas_planta": int(llantas_planta or 0),
                        "es_primer_venta": False,
                        "rango_inactividad": _ClientesReports._segmento_para(
                            dias, SEGMENTOS_RANGO
                        ),
                    }
                )

            # ── PRIMER VENTA (sin historial + con contacto) ──
            if incluir_primer_venta:
                sin_historial_ids = (
                    session.query(Llanta.cliente_id)
                    .filter(Llanta.cliente_id.isnot(None))
                    .distinct()
                )
                con_contacto = or_(
                    func.coalesce(Cliente.celular, "") != "",
                    func.coalesce(Cliente.telefono, "") != "",
                    func.coalesce(Cliente.email, "") != "",
                )
                nuevos = (
                    session.query(
                        Cliente.id,
                        Cliente.nombre,
                        Cliente.telefono,
                        Cliente.celular,
                        Cliente.nit,
                        Cliente.email,
                        Cliente.ciudad,
                    )
                    .filter(Cliente.id.notin_(sin_historial_ids), con_contacto)
                    .order_by(Cliente.nombre)
                    .all()
                )
                for (cid, nombre, telefono, celular, nit, email, ciudad) in nuevos:
                    filas.append(
                        {
                            "nombre": nombre,
                            "contacto": telefono or celular or "",
                            "nit": nit or "",
                            "email": email or "",
                            "ciudad": ciudad or "",
                            "llantas_aptas": 0,
                            "segmento_dimension": "—",
                            "ultima_vez": "—",
                            "dias_sin_actividad": "1er venta",
                            "llantas_planta": 0,
                            "es_primer_venta": True,
                            "rango_inactividad": "1096+ días (3+ años)",
                        }
                    )

        return filas