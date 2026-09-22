"""LlantaService unit tests — lifecycle, state transitions, catalogs.

Uses the ``service_db`` fixture so every ``get_session()`` call inside the
service hits an isolated temporary database.
"""

import pytest

from src.modules.llantas.services.llanta_service import (
    COMBINACIONES_VALIDAS,
    ESTADOS_PROCESO,
    TRANSICIONES_VALIDAS,
    UBICACIONES_PLANTA,
    VEREDICTO_UBICACION,
    LlantaService,
)


@pytest.fixture(autouse=True)
def _clean(service_db):
    yield


def _crear_llanta(tiquete: str = "TQ-001", **kwargs):
    ok, res = LlantaService.crear(tiquete=tiquete, **kwargs)
    assert ok, f"crear falló: {res}"
    return res


class TestCrearLlanta:
    """LlantaService.crear — basic creation rules."""

    def test_crear_exitosa_estado_pendiente(self):
        llanta = _crear_llanta()
        assert llanta.tiquete == "TQ-001"
        assert llanta.estado == "PENDIENTE"
        # Flujo correcto 2: el ingreso siempre es Pendiente / Planta
        assert llanta.ubicacion_actual == "PLANTA"

    def test_crear_tiquete_vacio(self):
        ok, msg = LlantaService.crear(tiquete="   ")
        assert not ok
        assert isinstance(msg, str)
        assert "obligatorio" in msg

    def test_crear_tiquete_duplicado(self):
        _crear_llanta()
        ok, msg = LlantaService.crear(tiquete="TQ-001")
        assert not ok
        assert isinstance(msg, str)
        assert "ya existe" in msg.lower()

    def test_crear_con_campos_tecnicos(self):
        llanta = _crear_llanta(
            tiquete="TQ-002",
            ancho=295,
            perfil=80,
            rin=22,
            precio_venta=1500000.0,
            costo_produccion=800000.0,
        )
        assert llanta.ancho == 295
        assert llanta.precio_venta == 1500000.0


class TestTiqueteExiste:
    """LlantaService.tiquete_existe — live duplicate validation."""

    def test_existe(self):
        _crear_llanta()
        assert LlantaService.tiquete_existe("TQ-001") is True

    def test_no_existe(self):
        assert LlantaService.tiquete_existe("NO-EXISTE") is False

    def test_vacio(self):
        assert LlantaService.tiquete_existe("  ") is False


class TestCambiarEstado:
    """LlantaService.cambiar_estado — transition matrix enforcement."""

    def test_transicion_valida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "APTA")
        assert ok
        assert "APTA" in msg

    def test_transicion_invalida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "REENCAUCHADA")
        assert not ok
        assert "Transición inválida" in msg

    def test_estado_invalido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "EXPLOTADA")
        assert not ok
        assert "Estado inválido" in msg

    def test_llanta_no_existe(self):
        ok, msg = LlantaService.cambiar_estado(99999, "APTA")
        assert not ok
        assert "no encontrada" in msg

    def test_historial_se_registra(self):
        llanta = _crear_llanta()
        LlantaService.cambiar_estado(llanta.id, "APTA")
        historial = LlantaService.obtener_historial_estados(llanta.id)
        assert len(historial) == 2  # PENDIENTE (crear) + APTA
        assert str(historial[0].estado) == "APTA"

    def test_estado_rechazada_sin_causa(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.cambiar_estado(llanta.id, "RECHAZADA")
        assert not ok
        assert "causa" in msg.lower()

    def test_estado_rechazada_con_causa(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.crear_causa_rechazo("93", "CAUSA CAMBIO ESTADO")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("93")
        assert causa is not None
        ok, msg = LlantaService.cambiar_estado(llanta.id, "RECHAZADA", causa.id)
        assert ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "RECHAZADA"
        assert llanta_actual.causa_rechazo_id == causa.id

    def test_estado_no_rechazada_no_guarda_causa(self):
        # Una causa pasada con un estado que no es RECHAZADA no se guarda
        llanta = _crear_llanta()
        ok, msg = LlantaService.crear_causa_rechazo("92", "CAUSA NO GUARDAR")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("92")
        ok, msg = LlantaService.cambiar_estado(llanta.id, "APTA", causa.id)
        assert ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.causa_rechazo_id is None

    def test_rechazada_a_apta(self):
        # Corrección de inspección inicial: RECHAZADA → APTA (limpia la causa)
        llanta = _crear_llanta()
        ok, msg = LlantaService.crear_causa_rechazo("91", "CAUSA RECHAZADA")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("91")
        ok, msg = LlantaService.cambiar_estado(llanta.id, "RECHAZADA", causa.id)
        assert ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "RECHAZADA"
        assert llanta_actual.causa_rechazo_id == causa.id

        ok, msg = LlantaService.cambiar_estado(llanta.id, "APTA")
        assert ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "APTA"
        assert llanta_actual.causa_rechazo_id is None  # la causa se limpia


class TestMoverUbicacion:
    """LlantaService.mover_ubicacion — location tracking."""

    def test_mover_valido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(llanta.id, "PLANTA")
        assert ok
        assert isinstance(msg, str)
        assert "PLANTA" in msg
        historial = LlantaService.obtener_historial_ubicaciones(llanta.id)
        assert len(historial) == 2  # PLANTA (crear) + PLANTA (movimiento)
        assert str(historial[0].ubicacion) == "PLANTA"

    def test_mover_invalido_por_estado(self):
        # Regla R2: PENDIENTE no puede estar en PRODUCCION
        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(llanta.id, "PRODUCCION")
        assert not ok
        assert "no puede estar en" in msg

    def test_ubicacion_invalida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(llanta.id, "MARTE")
        assert not ok
        assert "Ubicación inválida" in msg

    def test_llanta_no_existe(self):
        ok, msg = LlantaService.mover_ubicacion(99999, "PLANTA")
        assert not ok
        assert "no encontrada" in msg

    def test_mover_guarda_fecha_y_doc_salida(self):
        from datetime import date

        llanta = _crear_llanta()
        ok, msg = LlantaService.mover_ubicacion(
            llanta.id,
            "PLANTA",
            fecha_salida=date(2026, 9, 22),
            doc_salida="DOC-001",
        )
        assert ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.fecha_salida.date() == date(2026, 9, 22)
        assert llanta_actual.doc_salida == "DOC-001"


class TestAplicarVeredicto:
    """LlantaService.aplicar_veredicto — atomic estado + ubicación."""

    def test_veredicto_apta(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "APTA")
        assert ok
        assert "PRODUCCION" in msg

    def test_veredicto_rechazada_mueve_a_planta(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.crear_causa_rechazo("99", "CAUSA TEST")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("99")
        assert causa is not None
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA", causa.id)
        assert ok
        assert "PLANTA" in msg
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.causa_rechazo_id == causa.id

    def test_veredicto_rechazada_sin_causa(self):
        # En la inspección final la causa NO es obligatoria (solo en la
        # inspección inicial vía cambiar_estado).
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA")
        assert ok
        assert "PLANTA" in msg
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "RECHAZADA"
        assert llanta_actual.causa_rechazo_id is None

    def test_veredicto_rechazada_con_causa_invalida(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA", 99999)
        assert not ok
        assert "no existe" in msg

    def test_veredicto_invalido(self):
        llanta = _crear_llanta()
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "GANADORA")
        assert not ok
        assert "Veredicto inválido" in msg

    def test_veredicto_con_transicion_invalida(self):
        llanta = _crear_llanta()
        LlantaService.cambiar_estado(llanta.id, "APTA")
        # APTA no puede ir directo a PENDIENTE vía veredicto (no es veredicto)
        ok, _ = LlantaService.aplicar_veredicto(llanta.id, "APTA")
        assert not ok  # APTA → APTA ya no es válido; el reproceso es APTA → REPROCESO

    def test_veredicto_reproceso_mantiene_produccion(self):
        # Regla R7: inspección final NO pasa → REPROCESO, se mantiene en PRODUCCION
        llanta = _crear_llanta()
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPROCESO")
        assert ok
        assert "PRODUCCION" in msg
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "REPROCESO"
        assert llanta_actual.ubicacion_actual == "PRODUCCION"

    def test_veredicto_reproceso_a_reencauchada(self):
        # Reproceso pasa inspección final → REENCAUCHADA / PLANTA
        llanta = _crear_llanta()
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        LlantaService.aplicar_veredicto(llanta.id, "REPROCESO")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REENCAUCHADA")
        assert ok
        assert "PLANTA" in msg
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        assert llanta_actual.estado == "REENCAUCHADA"
        assert llanta_actual.ubicacion_actual == "PLANTA"

    def test_veredicto_reproceso_a_rechazada(self):
        # Reproceso no viable en inspección final → RECHAZADA / PLANTA
        llanta = _crear_llanta()
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        LlantaService.aplicar_veredicto(llanta.id, "REPROCESO")
        ok, msg = LlantaService.crear_causa_rechazo("95", "CAUSA REPROCESO")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("95")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA", causa.id)
        assert ok
        assert "PLANTA" in msg

    def test_veredicto_reencauchada_re_inspeccion(self):
        # REENCAUCHADA (terminada) admite re-inspección final → REPROCESO
        llanta = _crear_llanta()
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        LlantaService.aplicar_veredicto(llanta.id, "REENCAUCHADA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPROCESO")
        assert ok
        assert "PRODUCCION" in msg

    def test_veredicto_reencauchada_a_rechazada(self):
        # REENCAUCHADA re-inspección → RECHAZADA (con causa obligatoria)
        llanta = _crear_llanta(tiquete="TQ-RE2")
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        LlantaService.aplicar_veredicto(llanta.id, "REENCAUCHADA")
        ok, msg = LlantaService.crear_causa_rechazo("94", "CAUSA REENCAUCHADA")
        assert ok, msg
        causa = LlantaService.buscar_causa_rechazo("94")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "RECHAZADA", causa.id)
        assert ok
        assert "PLANTA" in msg

    def test_veredicto_reparada_desde_reencauchada_invalido(self):
        # REENCAUCHADA no admite REPARADA (solo REPROCESO/RECHAZADA)
        llanta = _crear_llanta()
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        LlantaService.aplicar_veredicto(llanta.id, "REENCAUCHADA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPARADA")
        assert not ok
        llanta_actual = LlantaService.obtener_por_id(llanta.id)
        # El veredicto inválido no modifica el estado
        assert llanta_actual.estado == "REENCAUCHADA"
        assert llanta_actual.ubicacion_actual == "PLANTA"


class TestReglaReparadaREP:
    """Regla R5: Reparada solo con diseño de banda REP."""

    def test_reparada_requiere_diseno_rep(self):
        ok, _ = LlantaService.crear_diseno("REP", "MIXTO")
        disenos = LlantaService.listar_disenos()
        diseno_rep = disenos[0]
        llanta = _crear_llanta(tiquete="TQ-REP", diseno_id=diseno_rep.id)
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPARADA")
        assert ok
        assert "REPARADA" in msg

    def test_reparada_rechazada_sin_diseno_rep(self):
        ok, _ = LlantaService.crear_diseno("VZY2", "MIXTO")
        disenos = LlantaService.listar_disenos()
        llanta = _crear_llanta(tiquete="TQ-NOREP", diseno_id=disenos[0].id)
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPARADA")
        assert not ok
        assert "Reparada solo se permite" in msg

    def test_reparada_sin_diseno_rechazada(self):
        llanta = _crear_llanta(tiquete="TQ-SINDISENO")
        LlantaService.aplicar_veredicto(llanta.id, "APTA")
        ok, msg = LlantaService.aplicar_veredicto(llanta.id, "REPARADA")
        assert not ok
        assert "sin diseño" in msg


class TestCRUDCatalogos:
    """LlantaService catalog CRUD — marcas, dimensiones, diseños, causas."""

    def test_crud_marca(self):
        ok, _ = LlantaService.crear_marca("BRIDGESTONE", "BS")
        assert ok
        ok, _ = LlantaService.crear_marca("BRIDGESTONE")
        assert not ok  # duplicado
        marcas = LlantaService.listar_marcas()
        assert len(marcas) == 1
        ok, _ = LlantaService.actualizar_marca(marcas[0].id, "BRIDGESTONE", "BRS")
        assert ok
        ok, _ = LlantaService.eliminar_marca(marcas[0].id)
        assert ok
        assert len(LlantaService.listar_marcas()) == 0

    def test_marca_con_llantas_no_se_elimina(self):
        ok, _ = LlantaService.crear_marca("GOODYEAR")
        marca = LlantaService.listar_marcas()[0]
        _crear_llanta(tiquete="TQ-M1", marca_id=marca.id)
        ok, msg = LlantaService.eliminar_marca(marca.id)
        assert not ok
        assert "usan esta marca" in msg

    def test_crud_dimension(self):
        ok, _ = LlantaService.crear_dimension(295, 80, 22)
        assert ok
        ok, _ = LlantaService.crear_dimension(295, 80, 22)
        assert not ok  # duplicado
        dims = LlantaService.listar_dimensiones()
        assert len(dims) == 1
        ok, _ = LlantaService.actualizar_dimension(dims[0].id, 295, 80, 22.5)
        assert ok
        ok, _ = LlantaService.eliminar_dimension(dims[0].id)
        assert ok

    def test_dimension_invalida(self):
        ok, msg = LlantaService.crear_dimension(0, 80, 22)
        assert not ok
        assert "positivos" in msg

    def test_dimension_ancho_decimal(self):
        # v2.6.0: ancho puede ser decimal (9.5R17.5)
        ok, msg = LlantaService.crear_dimension(9.5, None, 17.5)
        assert ok, msg
        dims = LlantaService.listar_dimensiones()
        assert any(d.ancho == 9.5 for d in dims)
        assert any(d.display == "9.5 R17.5" for d in dims)

    def test_dimension_con_sufijo(self):
        # v2.6.0: sufijo visible (215/75R16C)
        ok, msg = LlantaService.crear_dimension(215, 75, 16, sufijo="C")
        assert ok, msg
        dims = LlantaService.listar_dimensiones()
        con_sufijo = [d for d in dims if d.sufijo == "C"]
        assert len(con_sufijo) == 1
        assert con_sufijo[0].display == "215/75 R16C"

    def test_dimension_sin_ancho(self):
        # Formato H78-15: ancho None permitido
        ok, msg = LlantaService.crear_dimension(None, None, 15)
        assert ok, msg

    def test_dimension_duplicado_con_sufijo_distinto(self):
        # Misma medida con y sin sufijo son dimensiones distintas
        ok, _ = LlantaService.crear_dimension(295, 80, 22.5, sufijo="")
        ok2, _ = LlantaService.crear_dimension(295, 80, 22.5, sufijo="U")
        assert ok and ok2

    def test_crud_diseno(self):
        ok, _ = LlantaService.crear_diseno("Direccional Premium", "DIRECCIONAL")
        assert ok
        ok, _ = LlantaService.crear_diseno("Direccional Premium", "DIRECCIONAL")
        assert not ok  # duplicado
        disenos = LlantaService.listar_disenos()
        assert len(disenos) == 1
        ok, _ = LlantaService.actualizar_diseno(
            disenos[0].id, "Direccional Premium", "MIXTO"
        )
        assert ok
        ok, _ = LlantaService.eliminar_diseno(disenos[0].id)
        assert ok

    def test_diseno_tipo_invalido(self):
        ok, msg = LlantaService.crear_diseno("X", "DESCONOCIDO")
        assert not ok
        assert "Tipo inválido" in msg

    def test_crud_causa_rechazo(self):
        ok, _ = LlantaService.crear_causa_rechazo("C01", "Corte lateral")
        assert ok
        ok, _ = LlantaService.crear_causa_rechazo("C01", "Otro")
        assert not ok  # código duplicado
        causas = LlantaService.listar_causas_rechazo()
        assert len(causas) == 1
        ok, _ = LlantaService.actualizar_causa_rechazo(
            causas[0].id, "C01", "Corte lateral profundo", "ESTRUCTURAL"
        )
        assert ok
        ok, _ = LlantaService.eliminar_causa_rechazo(causas[0].id)
        assert ok


class TestConsultas:
    """LlantaService query methods."""

    def test_listar_y_buscar(self):
        _crear_llanta(tiquete="TQ-A1")
        _crear_llanta(tiquete="TQ-A2")
        llantas, total = LlantaService.listar_llantas()
        assert len(llantas) == 2
        assert total == 2
        por_term, _ = LlantaService.buscar(term="TQ-A2")
        assert len(por_term) == 1
        por_estado, _ = LlantaService.buscar(estado="PENDIENTE")
        assert len(por_estado) == 2

    def test_listar_paginado(self):
        for i in range(3):
            _crear_llanta(tiquete=f"TQ-P{i}")
        page1, total = LlantaService.listar_llantas(limite=2, offset=0)
        page2, _ = LlantaService.listar_llantas(limite=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1
        assert total == 3
        # Sin duplicados entre paginas
        ids = {l.id for l in page1} | {l.id for l in page2}
        assert len(ids) == 3

    def test_obtener_por_id(self):
        llanta = _crear_llanta()
        assert LlantaService.obtener_por_id(llanta.id) is not None
        assert LlantaService.obtener_por_id(99999) is None

    def test_contar_por_estado(self):
        _crear_llanta(tiquete="TQ-C1")
        _crear_llanta(tiquete="TQ-C2")
        conteo = LlantaService.contar_por_estado()
        assert conteo.get("PENDIENTE") == 2


class TestMatriz:
    """Static state-machine contract (flujo correcto 2)."""

    def test_estados_proceso_completos(self):
        assert set(ESTADOS_PROCESO) == {
            "PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA",
            "REPROCESO",
        }

    def test_matriz_transiciones(self):
        assert TRANSICIONES_VALIDAS["PENDIENTE"] == {"APTA", "RECHAZADA"}
        # Inspección final: 4 veredictos fijos (REENCAUCHADA/RECHAZADA/REPARADA/REPROCESO)
        assert TRANSICIONES_VALIDAS["APTA"] == {
            "REENCAUCHADA", "REPARADA", "RECHAZADA", "REPROCESO",
        }
        assert TRANSICIONES_VALIDAS["REPROCESO"] == {
            "REENCAUCHADA", "REPARADA", "RECHAZADA",
        }
        # Re-inspección final de llantas reencauchadas → REPROCESO | RECHAZADA
        assert TRANSICIONES_VALIDAS["REENCAUCHADA"] == {"REPROCESO", "RECHAZADA"}
        assert TRANSICIONES_VALIDAS["REPARADA"] == set()
        # Corrección de inspección inicial: RECHAZADA puede pasar a APTA
        assert TRANSICIONES_VALIDAS["RECHAZADA"] == {"APTA"}

    def test_ubicaciones_validas(self):
        assert set(UBICACIONES_PLANTA) == {"PRODUCCION", "PLANTA", "CLIENTE"}

    def test_veredicto_ubicacion(self):
        assert VEREDICTO_UBICACION == {
            "APTA": "PRODUCCION",
            "REENCAUCHADA": "PLANTA",
            "REPARADA": "PLANTA",
            "RECHAZADA": "PLANTA",
            "REPROCESO": "PRODUCCION",
        }

    def test_combinaciones_validas_r1_r6(self):
        # R1: APTA no en CLIENTE
        assert "CLIENTE" not in COMBINACIONES_VALIDAS["APTA"]
        # R2: PENDIENTE no en PRODUCCION
        assert "PRODUCCION" not in COMBINACIONES_VALIDAS["PENDIENTE"]
        # R3/R4: REENCAUCHADA/REPARADA no en PRODUCCION
        assert "PRODUCCION" not in COMBINACIONES_VALIDAS["REENCAUCHADA"]
        assert "PRODUCCION" not in COMBINACIONES_VALIDAS["REPARADA"]
        # R6: CLIENTE solo admite REENCAUCHADA/REPARADA/RECHAZADA
        assert "CLIENTE" not in COMBINACIONES_VALIDAS["PENDIENTE"]
        assert "CLIENTE" not in COMBINACIONES_VALIDAS["APTA"]
        assert COMBINACIONES_VALIDAS["RECHAZADA"] == {"PLANTA", "CLIENTE"}
        assert COMBINACIONES_VALIDAS["REENCAUCHADA"] == {"PLANTA", "CLIENTE"}
        assert COMBINACIONES_VALIDAS["REPARADA"] == {"PLANTA", "CLIENTE"}
        # R7: REPROCESO solo en PRODUCCION
        assert COMBINACIONES_VALIDAS["REPROCESO"] == {"PRODUCCION"}
