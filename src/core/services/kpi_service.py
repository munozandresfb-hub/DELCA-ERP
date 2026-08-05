from datetime import datetime

from sqlalchemy import func

from src.core.models.kpi_model import KpiConfig, KpiHistorico
from src.database.engine import get_session
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta


class KpiService:
    """Service for KPI configuration and monthly historical records."""

    # =========================================================
    # Config (punto de equilibrio)
    # =========================================================

    @staticmethod
    def obtener_config() -> KpiConfig | None:
        """Get the singleton KPI config row. Creates default if needed."""
        with get_session() as session:
            config = session.query(KpiConfig).first()
            if config:
                session.expunge(config)
                return config
            # Create default config
            config = KpiConfig(
                punto_equilibrio_produccion=100,
                punto_equilibrio_financiero=1000000.0,
            )
            session.add(config)
            session.flush()
            session.expunge(config)
            return config

    @staticmethod
    def guardar_config(
        produccion: int, financiero: float
    ) -> tuple[bool, str]:
        """Save break-even values."""
        if produccion <= 0:
            return False, "El punto de equilibrio de producción debe ser mayor a cero"
        if financiero <= 0:
            return False, "El punto de equilibrio financiero debe ser mayor a cero"

        with get_session() as session:
            config = session.query(KpiConfig).first()
            if not config:
                config = KpiConfig(
                    punto_equilibrio_produccion=produccion,
                    punto_equilibrio_financiero=financiero,
                )
                session.add(config)
            else:
                config.punto_equilibrio_produccion = produccion
                config.punto_equilibrio_financiero = financiero
            return True, "Punto de equilibrio actualizado"

    # =========================================================
    # Monthly historical records
    # =========================================================

    @staticmethod
    def calcular_mes_actual() -> dict:
        """Calculate current month's KPI data (production count + invoicing)."""
        with get_session() as session:
            now = datetime.now()
            inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Llantas producidas: reached REENCAUCHADA state this month
            llantas_producidas = (
                session.query(func.count(func.distinct(EstadoLlanta.llanta_id)))
                .filter(
                    EstadoLlanta.estado == "REENCAUCHADA",
                    EstadoLlanta.fecha >= inicio_mes,
                )
                .scalar()
            )

            # Facturación del mes
            facturacion_total = (
                session.query(func.coalesce(func.sum(Factura.total), 0))
                .filter(Factura.fecha_emision >= inicio_mes)
                .scalar()
            )

        return {
            "llantas_producidas": llantas_producidas,
            "facturacion_total": float(facturacion_total),
        }

    @staticmethod
    def generar_registro_mes() -> dict:
        """Generate or update current month's KPI historical record."""
        with get_session() as session:
            now = datetime.now()
            anio = now.year
            mes = now.month

            data = KpiService.calcular_mes_actual()

            # Upsert: find existing record for this month
            registro = (
                session.query(KpiHistorico)
                .filter(
                    KpiHistorico.anio == anio,
                    KpiHistorico.mes == mes,
                )
                .first()
            )

            if registro:
                registro.llantas_producidas = data["llantas_producidas"]
                registro.facturacion_total = data["facturacion_total"]
            else:
                registro = KpiHistorico(
                    anio=anio,
                    mes=mes,
                    llantas_producidas=data["llantas_producidas"],
                    facturacion_total=data["facturacion_total"],
                )
                session.add(registro)
                session.flush()
                session.expunge(registro)

            return data

    @staticmethod
    def obtener_historicos() -> list[dict]:
        """Get all historical KPI records ordered by year/month desc."""
        with get_session() as session:
            registros = (
                session.query(KpiHistorico)
                .order_by(KpiHistorico.anio.desc(), KpiHistorico.mes.desc())
                .all()
            )
            result = []
            for r in registros:
                session.expunge(r)
                result.append({
                    "id": r.id,
                    "anio": r.anio,
                    "mes": r.mes,
                    "periodo": f"{r.mes:02d}/{r.anio}",
                    "llantas_producidas": r.llantas_producidas,
                    "facturacion_total": float(r.facturacion_total),
                })
            return result

    @staticmethod
    def obtener_actual_con_config() -> dict:
        """Get current month KPI data with all 5 dashboard KPIs.

        Returns:
            KPI 1: llantas_producidas / punto_equilibrio_produccion
            KPI 2: facturacion_total / punto_equilibrio_financiero
            KPI 3: retiradas_mes / llantas_producidas (tasa de retiro)
            KPI 4: clientes_regresan / clientes_llamados (tasa de recompra)
            KPI 5: llantas_producidas / recibidas_mes (tasa de conversion)
        """
        config = KpiService.obtener_config()
        data = KpiService.generar_registro_mes()

        pp = config.punto_equilibrio_produccion if config else 100
        pf = float(config.punto_equilibrio_financiero) if config else 1000000.0

        lp = data["llantas_producidas"]
        ft = data["facturacion_total"]

        with get_session() as session:
            now = datetime.now()
            inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # KPI 3: retiradas del mes (movimiento a CLIENTE)
            retiradas_mes = (
                session.query(func.count(func.distinct(UbicacionLlanta.llanta_id)))
                .filter(
                    UbicacionLlanta.ubicacion == "CLIENTE",
                    UbicacionLlanta.fecha >= inicio_mes,
                )
                .scalar()
            )

            # KPI 5: recibidas del mes (PENDIENTE)
            recibidas_mes = (
                session.query(func.count(func.distinct(EstadoLlanta.llanta_id)))
                .filter(
                    EstadoLlanta.estado == "PENDIENTE",
                    EstadoLlanta.fecha >= inicio_mes,
                )
                .scalar()
            )

            # KPI 4: clientes llamados (con >= 1 llanta) y que regresan (>= 2 llantas)
            subq = (
                session.query(
                    Llanta.cliente_id,
                    func.count(Llanta.id).label("total_llantas"),
                )
                .group_by(Llanta.cliente_id)
                .subquery()
            )
            clientes_llamados = session.query(func.count(subq.c.cliente_id)).scalar()
            clientes_regresan = (
                session.query(func.count(subq.c.cliente_id))
                .filter(subq.c.total_llantas >= 2)
                .scalar()
            )

        # ── Calculate percentages ──
        pct_produccion = round((lp / pp) * 100, 1) if pp > 0 else 0
        pct_financiero = round((ft / pf) * 100, 1) if pf > 0 else 0
        pct_retiro = round((retiradas_mes / lp) * 100, 1) if lp > 0 else 0
        pct_recompra = (
            round((clientes_regresan / clientes_llamados) * 100, 1)
            if clientes_llamados and clientes_llamados > 0
            else 0
        )
        pct_conversion = round((lp / recibidas_mes) * 100, 1) if recibidas_mes > 0 else 0

        return {
            # KPI 1: Produccion
            "llantas_producidas": lp,
            "punto_equilibrio_produccion": pp,
            "pct_produccion": pct_produccion,
            "produccion_ok": lp >= pp,
            # KPI 2: Facturacion
            "facturacion_total": ft,
            "punto_equilibrio_financiero": pf,
            "pct_financiero": pct_financiero,
            "financiero_ok": ft >= pf,
            # KPI 3: Retiro
            "retiradas_mes": retiradas_mes,
            "pct_retiro": pct_retiro,
            # KPI 4: Recompra
            "clientes_regresan": clientes_regresan or 0,
            "clientes_llamados": clientes_llamados or 0,
            "pct_recompra": pct_recompra,
            # KPI 5: Conversion
            "recibidas_mes": recibidas_mes,
            "pct_conversion": pct_conversion,
        }
