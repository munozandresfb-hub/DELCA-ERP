"""
Model registry — imports ALL SQLAlchemy models in dependency-safe order.

Import this module before any database operation in scripts, tests,
or REPL sessions to ensure all mappers are configured correctly:

    import src.database.registry  # noqa: F401

or:

    from src.database.registry import *

NOTE: This does NOT call Base.metadata.create_all(). That is the
caller's responsibility (typically main.py during app startup).
"""

# ─── Usuarios ────────────────────────────────────────────────
from src.modules.usuarios.models.rol_model import Rol  # noqa: F401
from src.modules.usuarios.models.usuario_model import Usuario  # noqa: F401
from src.modules.usuarios.models.permiso_model import (  # noqa: F401
    Permiso,
    rol_permiso,
)

# ─── Clientes ────────────────────────────────────────────────
from src.modules.clientes.models.cliente_model import Cliente  # noqa: F401

# ─── Llantas ─────────────────────────────────────────────────
from src.modules.llantas.models.llanta_model import Llanta  # noqa: F401
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta  # noqa: F401
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta  # noqa: F401
from src.modules.llantas.models.marca_llanta_model import MarcaLlanta  # noqa: F401
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta  # noqa: F401
from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta  # noqa: F401
from src.modules.llantas.models.causa_rechazo_model import CausaRechazo  # noqa: F401

# ─── Finanzas ────────────────────────────────────────────────
from src.modules.finanzas.models.factura_model import Factura  # noqa: F401
from src.modules.finanzas.models.factura_llanta_model import FacturaLlanta  # noqa: F401
from src.modules.finanzas.models.pago_model import Pago  # noqa: F401

# ─── Inventario ──────────────────────────────────────────────
from src.modules.inventario.models.producto_model import Producto  # noqa: F401
from src.modules.inventario.models.movimiento_inventario_model import MovimientoInventario  # noqa: F401
from src.modules.inventario.models.precio_producto_model import PrecioProducto  # noqa: F401
from src.modules.inventario.models.inventario_config_models import (  # noqa: F401
    CostoProduccionEstandar,
    PrecioVentaCliente,
    RecetaProduccion,
)

# ─── Auditoría ───────────────────────────────────────────────
from src.modules.auditoria.models.auditoria_model import Auditoria  # noqa: F401

# ─── Automatización ──────────────────────────────────────────
from src.modules.automatizacion.models.regla_model import (  # noqa: F401
    Alerta,
    ReglaAutomatizacion,
)

# ─── KPI ─────────────────────────────────────────────────────
from src.core.models.kpi_model import KpiConfig, KpiHistorico  # noqa: F401

# ─── WhatsApp (agente) — dentro del módulo automatizacion ──────────
from src.modules.automatizacion.whatsapp.modelos import WhatsappConversacion  # noqa: F401
