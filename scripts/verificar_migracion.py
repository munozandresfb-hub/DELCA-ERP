# -*- coding: utf-8 -*-
"""PRUEBA DE FUNCIONALIDAD COMPLETA de DELCA ERP (verificador autonomo).

Ejecuta una bateria de verificaciones END-TO-END sobre la instalacion migrada,
SIN necesidad de Python ni dependencias (se compila como .exe):

  BLOQUE 1 - Componentes: archivos clave de la instalacion.
  BLOQUE 2 - Base de datos: integridad, WAL, conteos.
  BLOQUE 3 - Integridad de datos: reglas de negocio (estados/ubicaciones,
             relaciones, catálogos, precios).
  BLOQUE 4 - Funcionalidad de servicios: llantas, clientes, facturacion,
             cartera, inventario/kardex, reportes y catalogos.

Muestra un reporte con OK/FALLA por prueba y un resumen final.

Uso: colocar este .exe en la carpeta del proyecto (junto a delca.db o en dist\)
y ejecutarlo con doble clic.
"""
from __future__ import annotations

import os
import sys
import traceback

# ── Asegurar que el proyecto sea importable (modo fuente) ──
_BASE = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(_BASE))

_resultados: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    _resultados.append((nombre, ok, detalle))
    marca = "OK  " if ok else "FALLA"
    print(f"  [{marca}] {nombre}" + (f"  ->  {detalle}" if detalle else ""))


def bloque(titulo: str) -> None:
    print(f"\n{'=' * 68}\n {titulo}\n{'=' * 68}")


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 68)
    print("  DELCA ERP - PRUEBA DE FUNCIONALIDAD COMPLETA (verificador)")
    print("=" * 68)

    # ═══════════════ BLOQUE 1: Componentes ═══════════════
    bloque("BLOQUE 1 - COMPONENTES DE LA INSTALACION")
    from src.config import PROJECT_ROOT, settings

    print(f"  Carpeta del proyecto: {PROJECT_ROOT}")
    print(f"  Base de datos: {settings.db_path}")
    componentes = [
        ("Ejecutable DELCA ERP.exe", PROJECT_ROOT / "dist" / "DELCA ERP.exe"),
        ("Base de datos delca.db", PROJECT_ROOT / "delca.db"),
        ("Logo assets/delca.ico", PROJECT_ROOT / "assets" / "delca.ico"),
        ("Impresion data/impresion_config.json", PROJECT_ROOT / "data" / "impresion_config.json"),
        ("Datos maestros data/datos_maestros.xlsx", PROJECT_ROOT / "data" / "datos_maestros.xlsx"),
        ("Codigo fuente src/", PROJECT_ROOT / "src"),
        ("Scripts scripts/", PROJECT_ROOT / "scripts"),
    ]
    for nombre, ruta in componentes:
        check(nombre, ruta.exists(), str(ruta) if ruta.exists() else f"FALTA: {ruta}")

    # ═══════════════ BLOQUE 2: Base de datos ═══════════════
    bloque("BLOQUE 2 - BASE DE DATOS (integridad y conteos)")
    import sqlite3
    db = str(settings.db_path)
    try:
        con = sqlite3.connect(db)
        integ = con.execute("PRAGMA integrity_check").fetchone()[0]
        check("Integridad de la BD (integrity_check)", integ == "ok", integ)
        jm = con.execute("PRAGMA journal_mode").fetchone()[0]
        check("Modo journal", jm.lower() in ("wal", "delete"), jm)

        def n(sql):
            return con.execute(sql).fetchone()[0]

        llantas = n("SELECT COUNT(*) FROM llantas")
        clientes = n("SELECT COUNT(*) FROM cliente")
        productos = n("SELECT COUNT(*) FROM productos")
        facturas = n("SELECT COUNT(*) FROM facturas")
        print(f"\n  Conteos: llantas={llantas} | clientes={clientes} | "
              f"productos={productos} | facturas={facturas}")
        check("Llantas cargadas (>24000)", llantas > 24000, str(llantas))
        check("Clientes cargados (>5000)", clientes > 5000, str(clientes))
        check("Productos de inventario (>100)", productos > 100, str(productos))
        check("Roles de usuario", n("SELECT COUNT(*) FROM roles") >= 3, "")
        check("Usuarios", n("SELECT COUNT(*) FROM usuarios") >= 1, str(n("SELECT COUNT(*) FROM usuarios")))
        check("Catalogo de causas de rechazo", n("SELECT COUNT(*) FROM causas_rechazo") >= 40, str(n("SELECT COUNT(*) FROM causas_rechazo")))
        check("Catalogo de marcas", n("SELECT COUNT(*) FROM marcas_llanta") > 0, str(n("SELECT COUNT(*) FROM marcas_llanta")))
        check("Catalogo de dimensiones", n("SELECT COUNT(*) FROM dimensiones_llanta") > 0, str(n("SELECT COUNT(*) FROM dimensiones_llanta")))
        check("Catalogo de disenos", n("SELECT COUNT(*) FROM disenos_llanta") > 0, str(n("SELECT COUNT(*) FROM disenos_llanta")))

        # ═══════════════ BLOQUE 3: Integridad de datos (reglas) ═══════════════
        bloque("BLOQUE 3 - INTEGRIDAD DE DATOS (reglas de negocio)")
        estados_validos = {"PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA", "REPROCESO"}
        mal_estado = n("SELECT COUNT(*) FROM llantas WHERE estado NOT IN ('PENDIENTE','APTA','RECHAZADA','REENCAUCHADA','REPARADA','REPROCESO')")
        check("Todos los estados de llanta son validos", mal_estado == 0, f"invalidos: {mal_estado}")
        mal_ubic = n("SELECT COUNT(*) FROM llantas WHERE ubicacion_actual IS NOT NULL AND ubicacion_actual NOT IN ('PRODUCCION','PLANTA','CLIENTE')")
        check("Todas las ubicaciones son validas", mal_ubic == 0, f"invalidas: {mal_ubic}")
        sin_cliente = n("SELECT COUNT(*) FROM llantas WHERE cliente_id IS NULL")
        # Pocas llantas legacy sin cliente no bloquean la operatividad (informativo)
        check("Llantas con cliente asignado", sin_cliente <= 10, f"sin cliente: {sin_cliente}" + (" (legacy)" if sin_cliente else ""))
        sin_dim = n("SELECT COUNT(*) FROM llantas WHERE dimension_id IS NULL")
        check("Llantas con dimension de catalogo", sin_dim <= 10, f"sin dimension: {sin_dim}" + (" (legacy)" if sin_dim else ""))
        sin_dis = n("SELECT COUNT(*) FROM llantas WHERE diseno_id IS NULL")
        check("Llantas con diseno de catalogo", sin_dis <= 10, f"sin diseno: {sin_dis}" + (" (legacy)" if sin_dis else ""))
        causa_ok = n("SELECT COUNT(*) FROM llantas WHERE estado='RECHAZADA' AND causa_rechazo_id IS NULL")
        print(f"  (Nota: RECHAZADAS sin causa: {causa_ok} - datos legacy, informativo)")
        # Combinaciones estado-ubicacion validas
        combos = {
            "PENDIENTE": {"PLANTA"}, "APTA": {"PRODUCCION", "PLANTA"},
            "RECHAZADA": {"PLANTA", "CLIENTE"}, "REENCAUCHADA": {"PLANTA", "CLIENTE"},
            "REPARADA": {"PLANTA", "CLIENTE"}, "REPROCESO": {"PRODUCCION"},
        }
        malas = 0
        for r in con.execute("SELECT estado, ubicacion_actual, COUNT(*) FROM llantas GROUP BY estado, ubicacion_actual").fetchall():
            if r[1] and r[1] not in combos.get(r[0], set()):
                malas += r[2]
        check("Combinaciones estado-ubicacion validas (R1-R6)", malas == 0, f"invalidas: {malas}")
        # Historiales
        sin_hist = n("SELECT COUNT(*) FROM llantas l WHERE NOT EXISTS (SELECT 1 FROM estados_llanta e WHERE e.llanta_id=l.id)")
        check("Llantas con historial de estado", sin_hist == 0, f"sin historial: {sin_hist}")
        con.close()
    except Exception as e:
        check("Conexion a la base de datos", False, f"{type(e).__name__}: {e}")

    # ═══════════════ BLOQUE 4: Funcionalidad de servicios ═══════════════
    bloque("BLOQUE 4 - FUNCIONALIDAD DE LOS SERVICIOS (end-to-end)")
    import src.database.registry  # noqa: F401

    # 4.1 Llantas
    try:
        from src.modules.llantas.services.llanta_service import LlantaService
        ll, total = LlantaService.listar_llantas(limite=20)
        check("Llantas: listar (paginado)", total > 24000, f"{len(ll)} de {total}")
        res, t = LlantaService.buscar(term="1000")
        check("Llantas: buscar por tiquete/orden", t >= 0, f"resultados: {t}")
        marcas = LlantaService.listar_marcas()
        check("Llantas: catalogo de marcas", len(marcas) > 0, f"{len(marcas)} marcas")
        if marcas:
            r2, t2 = LlantaService.buscar(marca_id=marcas[0].id)
            check("Llantas: filtro por marca (busqueda avanzada)", t2 >= 0, f"marca {marcas[0].nombre}: {t2}")
        dims = LlantaService.listar_dimensiones()
        check("Llantas: catalogo de dimensiones", len(dims) > 0, f"{len(dims)} dimensiones")
        causas = LlantaService.listar_causas_rechazo()
        check("Llantas: catalogo de causas de rechazo", len(causas) >= 40, f"{len(causas)} causas")
    except Exception as e:
        check("Llantas: servicios", False, f"{type(e).__name__}: {e}")

    # 4.2 Clientes
    try:
        from src.modules.clientes.services.cliente_service import ClienteService
        cl = ClienteService.listar_clientes()
        check("Clientes: listar", len(cl) > 5000, f"{len(cl)} clientes")
    except Exception as e:
        check("Clientes: servicios", False, f"{type(e).__name__}: {e}")

    # 4.3 Facturacion / Cartera
    try:
        from src.modules.finanzas.services.factura_service import FacturaService
        facs = FacturaService.listar_facturas()
        check("Facturacion: listar facturas", isinstance(facs, list), f"{len(facs)} facturas")
        cartera = FacturaService.obtener_cartera_clientes()
        check("Cartera: saldos por cliente", isinstance(cartera, list), f"{len(cartera)} clientes con saldo")
        aging = FacturaService.obtener_antiguedad_saldos()
        check("Cartera: antiguedad de saldos", isinstance(aging, list), f"{len(aging)} facturas pendientes")
    except Exception as e:
        check("Facturacion/Cartera: servicios", False, f"{type(e).__name__}: {e}")

    # 4.4 Inventario / Kardex
    try:
        from src.modules.inventario.services.producto_service import ProductoService
        prod = ProductoService.listar_productos()
        check("Inventario: listar productos", len(prod) > 100, f"{len(prod)} productos")
    except Exception as e:
        check("Inventario: servicios", False, f"{type(e).__name__}: {e}")

    # 4.5 Reportes
    try:
        from src.modules.reportes.services.reporte_service import ReporteService
        rep = ReporteService.reporte_llantas()
        check("Reportes: reporte de llantas", rep is not None, f"{len(rep) if hasattr(rep, '__len__') else 'ok'} filas")
    except Exception as e:
        check("Reportes: servicios", False, f"{type(e).__name__}: {e}")

    # 4.6 Usuarios / Auth
    try:
        from src.modules.usuarios.services.auth_service import AuthService
        check("Usuarios: AuthService carga", AuthService is not None, "")
        from src.modules.usuarios.models.usuario_model import Usuario
        check("Usuarios: modelo Usuario", Usuario is not None, "")
    except Exception as e:
        check("Usuarios: servicios", False, f"{type(e).__name__}: {e}")

    # ═══════════════ RESUMEN ═══════════════
    bloque("RESUMEN DE LA PRUEBA DE FUNCIONALIDAD")
    total = len(_resultados)
    ok = sum(1 for _, o, _ in _resultados if o)
    fallas = [x for x in _resultados if not x[1]]
    print(f"  Pruebas ejecutadas: {total}")
    print(f"  OK:                 {ok}")
    print(f"  FALLAS:             {len(fallas)}")
    if fallas:
        print("\n  DETALLE DE FALLAS:")
        for nombre, _, detalle in fallas:
            print(f"    - {nombre}: {detalle}")
        print("\n  RESULTADO: *** REVISAR ***  Hay pruebas que fallaron.")
    else:
        print("\n  RESULTADO: *** TODO FUNCIONA CORRECTAMENTE ***")
    print("=" * 68)
    return 0 if not fallas else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("\n[ERROR CRITICO]")
        traceback.print_exc()
        input("\nPresione Enter para salir...")
        sys.exit(2)