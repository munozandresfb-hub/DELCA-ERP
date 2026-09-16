from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from src.database.engine import get_session
from src.modules.inventario.models.inventario_config_models import RecetaProduccion
from src.modules.inventario.models.producto_model import Producto
from src.modules.inventario.services.producto_service import ProductoService
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service._core import formatear_orden, formatear_tiquete
from src.modules.llantas.services.llanta_service import ESTADOS_TERMINADAS


class InventarioKpiService:
    """KPI calculations and reports for the inventory dashboard."""

    @staticmethod
    def resumen_kpis() -> dict:
        """Calculate all KPIs for the inventory dashboard."""
        with get_session() as session:
            # Raw material stock & value
            mp_query = (
                session.query(
                    func.sum(Producto.stock),
                    func.sum(Producto.stock * Producto.costo_unitario),
                )
                .filter(Producto.categoria == "MATERIA_PRIMA")
                .first()
                or (0, 0)
            )
            mp_disponible = float(mp_query[0] or 0)
            valor_inventario = float(mp_query[1] or 0)

            # Finished tires in plant (no entregadas al cliente) — costo/precio del catálogo
            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )
            idx = indice_precios(session)
            terminadas_rows = (
                session.query(Llanta)
                .filter(
                    Llanta.estado.in_(ESTADOS_TERMINADAS),
                    (Llanta.ubicacion_actual.is_(None))
                    | (Llanta.ubicacion_actual != "CLIENTE"),
                )
                .all()
            )
            llantas_en_planta = len(terminadas_rows)
            costo_en_planta = 0.0
            precio_total = 0.0
            for ll in terminadas_rows:
                costo, precio = costo_precio(ll, idx)
                costo_en_planta += costo
                precio_total += precio
            margen_potencial = round(precio_total - costo_en_planta, 2)

            # Production capacity
            capacidad = InventarioKpiService._calcular_capacidad(session)

            return {
                "mp_disponible": round(mp_disponible, 2),
                "valor_inventario": round(valor_inventario, 2),
                "capacidad_prod": capacidad,
                "llantas_en_planta": llantas_en_planta,
                "costo_en_planta": round(costo_en_planta, 2),
                "margen_potencial": margen_potencial,
            }

    @staticmethod
    def _calcular_capacidad(session) -> int:
        """Estimate production capacity based on recipes and available MP."""
        recetas = (
            session.query(RecetaProduccion)
            .options(joinedload(RecetaProduccion.producto))
            .all()
        )
        if not recetas:
            return 0

        # Group by (diseno_id, dimension_id) → get max tires possible
        from collections import defaultdict

        capacidades: dict[tuple, list[float]] = defaultdict(list)
        for receta in recetas:
            producto = receta.producto
            if not producto or producto.stock is None or producto.stock <= 0:
                continue
            if receta.cantidad and receta.cantidad > 0:
                posibles = float(producto.stock) / float(receta.cantidad)
                capacidades[(receta.diseno_id, receta.dimension_id)].append(posibles)

        if not capacidades:
            return 0

        # Sum the max tires possible per recipe group
        total = 0
        for lst in capacidades.values():
            if lst:
                total += int(min(lst))  # bottleneck = limiting MP
        return total

    @staticmethod
    def materias_primas() -> list[Producto]:
        """List all raw material products."""
        return ProductoService.listar_productos(categoria="MATERIA_PRIMA")

    @staticmethod
    def terminadas_en_planta() -> list[dict]:
        """List finished tires in plant with computed fields."""
        hoy = datetime.now()
        resultados: list[dict] = []
        with get_session() as session:
            llantas = (
                session.query(Llanta)
                .options(
                    joinedload(Llanta.cliente),
                    joinedload(Llanta.dimension_obj),
                    joinedload(Llanta.diseno_obj),
                    joinedload(Llanta.marca_obj),
                )
                .filter(
                    Llanta.estado.in_(ESTADOS_TERMINADAS),
                    (Llanta.ubicacion_actual.is_(None))
                    | (Llanta.ubicacion_actual != "CLIENTE"),
                )
                .order_by(Llanta.fecha_ingreso.asc())
                .all()
            )
            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )
            idx = indice_precios(session)
            for ll in llantas:
                dias = (hoy - ll.fecha_ingreso).days if ll.fecha_ingreso else 0
                costo, precio = costo_precio(ll, idx)
                resultados.append({
                    "id": ll.id,
                    "tiquete": formatear_tiquete(ll.tiquete),
                    "dimension": ll.dimension_obj.display if ll.dimension_obj else ll.dimension,
                    "diseno": ll.diseno_obj.nombre if ll.diseno_obj else "",
                    "marca": ll.marca_obj.nombre if ll.marca_obj else ll.marca,
                    "costo_produccion": costo,
                    "precio_venta": precio,
                    "margen": round(precio - costo, 2),
                    "cliente": ll.cliente.nombre if ll.cliente else "",
                    "cliente_id": ll.cliente_id,
                    "dias_en_planta": dias,
                    "fecha_ingreso": ll.fecha_ingreso,
                    "numero_orden": formatear_orden(ll.numero_orden, ll.consecutivo),
                })
        return resultados

    @staticmethod
    def reporte_antiguedad(dias_min: int, dias_max: int | None = None) -> list[dict]:
        """Filter finished tires by days in plant range."""
        hoy = datetime.now()
        todas = InventarioKpiService.terminadas_en_planta()
        filtradas = []
        for t in todas:
            if t["dias_en_planta"] >= dias_min:
                if dias_max is None or t["dias_en_planta"] <= dias_max:
                    filtradas.append(t)
        return filtradas

    @staticmethod
    def reporte_semanal(fecha_inicio: datetime, fecha_fin: datetime) -> list[dict]:
        """Tires retreaded (estado=REENCAUCHADA) in a date range."""
        with get_session() as session:
            llantas = (
                session.query(Llanta)
                .options(
                    joinedload(Llanta.cliente),
                    joinedload(Llanta.dimension_obj),
                    joinedload(Llanta.diseno_obj),
                )
                .filter(
                    Llanta.estado == "REENCAUCHADA",
                    Llanta.fecha_ingreso >= fecha_inicio,
                    Llanta.fecha_ingreso <= fecha_fin,
                )
                .order_by(Llanta.fecha_ingreso.desc())
                .all()
            )
            from src.modules.llantas.services.costo_precio import (
                costo_precio,
                indice_precios,
            )
            idx = indice_precios(session)
            return [
                {
                    "tiquete": formatear_tiquete(ll.tiquete),
                    "dimension": ll.dimension_obj.display if ll.dimension_obj else ll.dimension,
                    "diseno": ll.diseno_obj.nombre if ll.diseno_obj else "",
                    "cliente": ll.cliente.nombre if ll.cliente else "",
                    "costo": round(costo_precio(ll, idx)[0], 2),
                    "precio": round(costo_precio(ll, idx)[1], 2),
                    "margen": round(costo_precio(ll, idx)[1] - costo_precio(ll, idx)[0], 2),
                    "estado": ll.estado,
                    "fecha": ll.fecha_ingreso,
                }
                for ll in llantas
            ]
