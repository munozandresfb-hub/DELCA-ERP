"""Tests del módulo WhatsApp (envío, firma, parseo, contexto, agente sin red)."""

import json

import pytest

from src.modules.automatizacion.whatsapp.contexto_cliente import normalizar_telefono
from src.modules.automatizacion.whatsapp.whatsapp_service import (
    parsear_mensaje_entrante,
    verificar_firma,
)


class TestNormalizarTelefono:
    def test_formato_internacional(self):
        assert normalizar_telefono("573001234567") == "573001234567"

    def test_prefijo_colombia_plus(self):
        assert normalizar_telefono("+57 300 123 4567") == "573001234567"

    def test_local_10_digitos(self):
        assert normalizar_telefono("3001234567") == "573001234567"

    def test_vacio(self):
        assert normalizar_telefono("") == ""


class TestVerificarFirma:
    def test_firma_correcta(self, monkeypatch):
        import hashlib
        import hmac

        from src.config import settings

        monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "secreto_test")
        payload = b'{"test": true}'
        expected = "sha256=" + hmac.new(
            b"secreto_test", payload, hashlib.sha256
        ).hexdigest()
        assert verificar_firma(payload, expected) is True

    def test_firma_incorrecta(self, monkeypatch):
        from src.config import settings

        monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "secreto_test")
        assert verificar_firma(b'{"test": true}', "sha256=deadbeef") is False

    def test_sin_header(self, monkeypatch):
        from src.config import settings

        monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "secreto_test")
        assert verificar_firma(b"{}", None) is False

    def test_sin_secret(self, monkeypatch):
        from src.config import settings

        monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
        assert verificar_firma(b"{}", "sha256=abc") is False


class TestParsearMensajeEntrante:
    def _payload(self):
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "573001234567",
                                        "type": "text",
                                        "text": {"body": "Hola, cómo va mi llanta?"},
                                        "timestamp": "1727000000",
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

    def test_parsea_texto(self):
        msgs = parsear_mensaje_entrante(self._payload())
        assert len(msgs) == 1
        assert msgs[0]["telefono"] == "573001234567"
        assert "llanta" in msgs[0]["texto"]

    def test_ignora_status_updates(self):
        msgs = parsear_mensaje_entrante({"entry": [{"changes": [{"value": {"statuses": [{}]}}]}]})
        assert msgs == []

    def test_payload_vacio(self):
        assert parsear_mensaje_entrante({}) == []

    def test_ignora_tipos_no_texto(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"from": "57x", "type": "image", "image": {}},
                                    {"from": "57x", "type": "text", "text": {"body": "ok"}},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        msgs = parsear_mensaje_entrante(payload)
        assert len(msgs) == 1
        assert msgs[0]["texto"] == "ok"


class TestContextoClienteSinBD:
    """Verifica que el módulo de contexto se importa sin romper la BD real."""

    def test_import(self):
        from src.modules.automatizacion.whatsapp.contexto_cliente import buscar_cliente_por_telefono

        assert callable(buscar_cliente_por_telefono)


class TestAgenteSinConfig:
    def test_respuesta_sin_api_key(self, monkeypatch):
        from src.config import settings

        monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
        from src.modules.automatizacion.whatsapp.agente import generar_respuesta

        resp = generar_respuesta("573001234567", "Hola")
        assert "no está configurado" in resp
