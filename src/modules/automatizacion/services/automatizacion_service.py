import json
from datetime import datetime, timedelta

from src.database.engine import get_session
from src.modules.automatizacion.models.regla_model import (
    Alerta,
    ReglaAutomatizacion,
)
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.inventario.models.producto_model import Producto
from src.modules.llantas.models.llanta_model import Llanta


class AutomatizacionService:
    """Automation rule evaluation and alert management."""

    RULE_DEFAULTS = [
        {
            "nombre": "Stock Bajo",
            "tipo": "STOCK_BAJO",
            "nivel": "WARNING",
            "config_json": json.dumps({"umbral": 10}),
        },
        {
            "nombre": "Cartera Vencida 30+",
            "tipo": "CARTERA_VENCIDA",
            "nivel": "WARNING",
            "config_json": json.dumps({"dias": 30}),
        },
        {
            "nombre": "Cartera Vencida 60+",
            "tipo": "CARTERA_VENCIDA",
            "nivel": "CRITICAL",
            "config_json": json.dumps({"dias": 60}),
        },
        {
            "nombre": "Llantas Listas para Entrega",
            "tipo": "LLANTAS_LISTAS",
            "nivel": "INFO",
            "config_json": json.dumps({}),
        },
    ]

    # =========================================================
    # Rule management
    # =========================================================

    @staticmethod
    def inicializar_reglas() -> None:
        """Create default rules if none exist."""
        with get_session() as session:
            existing = session.query(ReglaAutomatizacion).count()
            if existing > 0:
                return
            for rule_data in AutomatizacionService.RULE_DEFAULTS:
                regla = ReglaAutomatizacion(**rule_data)
                session.add(regla)

    @staticmethod
    def listar_reglas() -> list[ReglaAutomatizacion]:
        with get_session() as session:
            reglas = (
                session.query(ReglaAutomatizacion)
                .order_by(ReglaAutomatizacion.tipo)
                .all()
            )
            for r in reglas:
                session.expunge(r)
            return reglas

    @staticmethod
    def obtener_regla(regla_id: int) -> ReglaAutomatizacion | None:
        with get_session() as session:
            regla = (
                session.query(ReglaAutomatizacion)
                .filter(ReglaAutomatizacion.id == regla_id)
                .first()
            )
            if regla:
                session.expunge(regla)
            return regla

    @staticmethod
    def crear_regla(
        nombre: str,
        tipo: str,
        nivel: str,
        activa: bool = True,
        config_dict: dict | None = None,
    ) -> ReglaAutomatizacion:
        with get_session() as session:
            regla = ReglaAutomatizacion(
                nombre=nombre,
                tipo=tipo,
                nivel=nivel,
                activa=activa,
                config_json=json.dumps(config_dict or {}),
            )
            session.add(regla)
            session.flush()
            session.refresh(regla)
            session.expunge(regla)
            return regla

    @staticmethod
    def actualizar_regla(
        regla_id: int,
        nombre: str,
        tipo: str,
        nivel: str,
        activa: bool,
        config_dict: dict | None = None,
    ) -> tuple[bool, str]:
        with get_session() as session:
            regla = (
                session.query(ReglaAutomatizacion)
                .filter(ReglaAutomatizacion.id == regla_id)
                .first()
            )
            if not regla:
                return False, "Regla no encontrada"
            regla.nombre = nombre
            regla.tipo = tipo
            regla.nivel = nivel
            regla.activa = activa
            regla.config_json = json.dumps(config_dict or {})
            return True, "Regla actualizada"

    @staticmethod
    def eliminar_regla(regla_id: int) -> tuple[bool, str]:
        with get_session() as session:
            regla = (
                session.query(ReglaAutomatizacion)
                .filter(ReglaAutomatizacion.id == regla_id)
                .first()
            )
            if not regla:
                return False, "Regla no encontrada"
            session.delete(regla)
            return True, "Regla eliminada"

    @staticmethod
    def toggle_regla(regla_id: int) -> tuple[bool, str]:
        with get_session() as session:
            regla = (
                session.query(ReglaAutomatizacion)
                .filter(ReglaAutomatizacion.id == regla_id)
                .first()
            )
            if not regla:
                return False, "Regla no encontrada"
            regla.activa = not regla.activa
            estado = "activada" if regla.activa else "desactivada"
            return True, f"Regla {estado}"

    # =========================================================
    # Alert management
    # =========================================================

    @staticmethod
    def listar_alertas(
        solo_no_leidas: bool = False, limite: int = 100
    ) -> list[Alerta]:
        with get_session() as session:
            q = session.query(Alerta).order_by(
                Alerta.created_at.desc()
            )
            if solo_no_leidas:
                q = q.filter(Alerta.leida.is_(False))
            alertas = q.limit(limite).all()
            for a in alertas:
                session.expunge(a)
            return alertas

    @staticmethod
    def marcar_leida(alerta_id: int) -> None:
        with get_session() as session:
            session.query(Alerta).filter(Alerta.id == alerta_id).update(
                {"leida": True}
            )

    @staticmethod
    def marcar_todas_leidas() -> None:
        with get_session() as session:
            session.query(Alerta).filter(
                Alerta.leida.is_(False)
            ).update({"leida": True})

    @staticmethod
    def alertas_no_leidas_count() -> int:
        with get_session() as session:
            return (
                session.query(Alerta)
                .filter(Alerta.leida.is_(False))
                .count()
            )

    @staticmethod
    def limpiar_alertas(dias: int = 30) -> None:
        """Remove alerts older than N days."""
        cutoff = (datetime.now() - timedelta(days=dias)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        with get_session() as session:
            session.query(Alerta).filter(
                Alerta.created_at < cutoff
            ).delete()

    # =========================================================
    # Rule evaluation
    # =========================================================

    @staticmethod
    def _crear_alerta(
        tipo: str, mensaje: str, nivel: str, entidad_tipo: str | None = None, entidad_id: int | None = None
    ) -> bool:
        """Create a new alert, avoiding duplicates. Returns True if created."""
        with get_session() as session:
            # Check for existing unread alert of same type+entity
            if entidad_tipo and entidad_id:
                existing = (
                    session.query(Alerta)
                    .filter(
                        Alerta.tipo == tipo,
                        Alerta.entidad_tipo == entidad_tipo,
                        Alerta.entidad_id == entidad_id,
                        Alerta.leida.is_(False),
                    )
                    .first()
                )
                if existing:
                    return False  # Skip duplicate

            alerta = Alerta(
                tipo=tipo,
                mensaje=mensaje,
                nivel=nivel,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
            )
            session.add(alerta)
            return True

    @staticmethod
    def evaluar_reglas() -> int:
        """Evaluate all active rules and generate alerts. Returns alert count."""
        with get_session() as session:
            reglas = (
                session.query(ReglaAutomatizacion)
                .filter(ReglaAutomatizacion.activa.is_(True))
                .all()
            )
            alertas_creadas = 0

            for regla in reglas:
                config = {}
                if regla.config_json:
                    try:
                        config = json.loads(regla.config_json)
                    except (json.JSONDecodeError, TypeError):
                        config = {}

                if regla.tipo == "STOCK_BAJO":
                    umbral = config.get("umbral", 10)
                    productos = (
                        session.query(Producto)
                        .filter(
                            Producto.activo.is_(True),
                            Producto.stock < umbral,
                            Producto.stock > 0,
                        )
                        .all()
                    )
                    for p in productos:
                        if AutomatizacionService._crear_alerta(
                            tipo="STOCK_BAJO",
                            mensaje=f"Stock bajo: {p.nombre} ({p.sku}) — {p.stock} unidades",
                            nivel=regla.nivel,
                            entidad_tipo="producto",
                            entidad_id=p.id,
                        ):
                            alertas_creadas += 1

                elif regla.tipo == "CARTERA_VENCIDA":
                    dias = config.get("dias", 30)
                    hoy = datetime.now()
                    facturas = (
                        session.query(Factura)
                        .filter(
                            Factura.estado == "PENDIENTE",
                            Factura.saldo > 0,
                        )
                        .all()
                    )
                    for f in facturas:
                        delta = (hoy - f.fecha_emision).days
                        if delta >= dias:
                            cliente = (
                                session.query(Cliente)
                                .filter(Cliente.id == f.cliente_id)
                                .first()
                            )
                            nombre_cliente = cliente.nombre if cliente else "?"
                            if AutomatizacionService._crear_alerta(
                                tipo="CARTERA_VENCIDA",
                                mensaje=f"Factura {f.numero} — {nombre_cliente} — "
                                f"${f.saldo:,.2f} ({delta} días vencida)",
                                nivel=regla.nivel,
                                entidad_tipo="factura",
                                entidad_id=f.id,
                            ):
                                alertas_creadas += 1

                elif regla.tipo == "LLANTAS_LISTAS":
                    llantas = (
                        session.query(Llanta)
                        .filter(
                            Llanta.estado == "REENCAUCHADA",
                            Llanta.ubicacion_actual == "PLANTA",
                        )
                        .all()
                    )
                    # Only alert if there are entregadas without a recent alert
                    for ll in llantas:
                        if AutomatizacionService._crear_alerta(
                            tipo="LLANTAS_LISTAS",
                            mensaje=f"Llanta {ll.tiquete} — "
                            f"{ll.marca or 'N/M'} — lista para entrega",
                            nivel=regla.nivel,
                            entidad_tipo="llanta",
                            entidad_id=ll.id,
                        ):
                            alertas_creadas += 1

            return alertas_creadas
