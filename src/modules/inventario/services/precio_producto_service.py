from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.database.engine import get_session
from src.modules.inventario.models.precio_producto_model import PrecioProducto
from src.modules.llantas.services.llanta_service import LlantaService

try:
    import openpyxl as _openpyxl

    HAS_OPENPYXL = True
except ImportError:
    _openpyxl = None  # type: ignore[assignment]
    HAS_OPENPYXL = False


class PrecioProductoService:
    """CRUD for master price list (PrecioProducto)."""

    @staticmethod
    def listar(
        diseno_id: int | None = None,
        dimension_id: int | None = None,
    ) -> list[PrecioProducto]:
        with get_session() as session:
            q = session.query(PrecioProducto)
            if diseno_id:
                q = q.filter(PrecioProducto.diseno_id == diseno_id)
            if dimension_id:
                q = q.filter(PrecioProducto.dimension_id == dimension_id)
            resultados = q.order_by(PrecioProducto.diseno_id).all()
            for r in resultados:
                session.expunge(r)
            return resultados

    @staticmethod
    def guardar(
        diseno_id: int,
        dimension_id: int,
        costo_fabricacion: Decimal,
        precio_minimo: Decimal,
        precio_medio: Decimal,
        precio_normal: Decimal,
    ) -> tuple[bool, str]:
        with get_session() as session:
            existente = (
                session.query(PrecioProducto)
                .filter(
                    PrecioProducto.diseno_id == diseno_id,
                    PrecioProducto.dimension_id == dimension_id,
                )
                .first()
            )
            if existente:
                existente.costo_fabricacion = costo_fabricacion
                existente.precio_minimo = precio_minimo
                existente.precio_medio = precio_medio
                existente.precio_normal = precio_normal
            else:
                nuevo = PrecioProducto(
                    diseno_id=diseno_id,
                    dimension_id=dimension_id,
                    costo_fabricacion=costo_fabricacion,
                    precio_minimo=precio_minimo,
                    precio_medio=precio_medio,
                    precio_normal=precio_normal,
                )
                session.add(nuevo)
            return True, "Precio guardado"

    @staticmethod
    def eliminar(precio_id: int) -> tuple[bool, str]:
        with get_session() as session:
            r = (
                session.query(PrecioProducto)
                .filter(PrecioProducto.id == precio_id)
                .first()
            )
            if not r:
                return False, "Precio no encontrado"
            session.delete(r)
            return True, "Precio eliminado"

    # ── Excel import ──────────────────────────────────────────────────

    @staticmethod
    def importar_desde_excel(ruta: str | Path) -> tuple[bool, str]:
        """Import prices from an Excel file.

        Expected columns:
            Diseño, Dimensión, Costo Fabricación, Precio Mínimo, Precio Medio, Precio Normal

        Rows are matched by (Diseño nombre, Dimensión display) and upserted.
        """
        if not HAS_OPENPYXL:
            return False, "openpyxl no está instalado. Ejecute: pip install openpyxl"

        wb = _openpyxl.load_workbook(ruta, data_only=True)
        ws = wb.active
        if ws is None:
            return False, "El archivo Excel no tiene hojas"

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        if not rows:
            return False, "El archivo Excel está vacío (solo encabezados)"

        # Build lookup maps: nombre→id
        disenos_map: dict[str, int] = {
            d.nombre: d.id for d in LlantaService.listar_disenos()
        }
        dimensiones_map: dict[str, int] = {
            m.display: m.id for m in LlantaService.listar_dimensiones()
        }

        importados = 0
        errores: list[str] = []

        for i, row in enumerate(rows, start=2):
            if not row or row[0] is None:
                continue
            diseno_nombre = str(row[0]).strip()
            dimension_display = str(row[1]).strip()
            diseno_id = disenos_map.get(diseno_nombre)
            dimension_id = dimensiones_map.get(dimension_display)
            if diseno_id is None:
                errores.append(f"Fila {i}: Diseño '{diseno_nombre}' no encontrado")
                continue
            if dimension_id is None:
                errores.append(f"Fila {i}: Dimensión '{dimension_display}' no encontrada")
                continue
            try:
                costo = Decimal(str(row[2] or "0"))
                minimo = Decimal(str(row[3] or "0"))
                medio = Decimal(str(row[4] or "0"))
                normal = Decimal(str(row[5] or "0"))
            except Exception as e:
                errores.append(f"Fila {i}: Error numérico → {e}")
                continue
            PrecioProductoService.guardar(diseno_id, dimension_id, costo, minimo, medio, normal)
            importados += 1

        resumen = f"{importados} precios importados"
        if errores:
            resumen += f", {len(errores)} errores:\n" + "\n".join(errores[:10])
            if len(errores) > 10:
                resumen += f"\n... y {len(errores) - 10} más"
        return True, resumen
