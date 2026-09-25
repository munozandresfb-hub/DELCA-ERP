"""Servidor webhook de WhatsApp para DELCA ERP.

Recibe los eventos de la WhatsApp Cloud API (Meta):
- GET  /webhook  → verificación inicial (hub.mode / hub.verify_token / hub.challenge)
- POST /webhook  → mensajes entrantes (firma X-Hub-Signature-256 verificada)

Al recibir un mensaje:
  1. Verifica la firma (rechaza si no coincide).
  2. Parsea el mensaje entrante.
  3. Si WHATSAPP_AGENT_ENABLED=true: consulta el historial reciente de la
     conversación, genera la respuesta con el agente IA y la envía por la
     Cloud API.
  4. Registra la conversación en la BD (tabla whatsapp_conversaciones).

Ejecutar como proceso independiente (no bloquea la GUI):
  .venv\\Scripts\\python.exe -m src.modules.automatizacion.whatsapp.servidor_webhook

La URL pública la expone un túnel (Cloudflare Tunnel/ngrok) apuntando al
puerto local WHATSAPP_WEBHOOK_PORT (default 9090).
"""

import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.config import settings
from src.modules.automatizacion.whatsapp.agente import generar_respuesta
from src.modules.automatizacion.whatsapp.modelos import WhatsappConversacion
from src.modules.automatizacion.whatsapp.whatsapp_service import (
    enviar_mensaje,
    parsear_mensaje_entrante,
    verificar_firma,
)

logger = logging.getLogger("delca.whatsapp.webhook")


def _registrar_conversacion(
    telefono: str, direccion: str, contenido: str, origen: str = "AGENTE"
) -> None:
    """Guarda un turno de la conversación (contexto para el agente)."""
    from src.database.engine import SessionLocal

    session = SessionLocal()
    try:
        session.add(
            WhatsappConversacion(
                telefono=telefono,
                direccion=direccion,
                contenido=contenido,
                origen=origen,
                fecha=datetime.now().isoformat(timespec="seconds"),
            )
        )
        session.commit()
    except Exception as e:
        logger.error("Error guardando conversación: %s", e, exc_info=True)
        session.rollback()
    finally:
        session.close()


def _historial_reciente(telefono: str, limite: int = 10) -> list[dict[str, str]]:
    """Devuelve los últimos turnos de la conversación (IN/OUT alternados)."""
    from src.database.engine import SessionLocal

    session = SessionLocal()
    try:
        filas = (
            session.query(WhatsappConversacion)
            .filter(WhatsappConversacion.telefono == telefono)
            .order_by(WhatsappConversacion.id.desc())
            .limit(limite)
            .all()
        )
        # Reconstruir en orden cronológico (el último turno es el más reciente)
        historial = []
        for f in reversed(filas):
            historial.append(
                {
                    "rol": "user" if f.direccion == "IN" else "assistant",
                    "contenido": f.contenido,
                }
            )
        return historial
    finally:
        session.close()


def _procesar_mensaje(telefono: str, texto: str) -> None:
    """Orquesta: historial → agente → envío → registro."""
    _registrar_conversacion(telefono, "IN", texto, origen="SISTEMA")

    if not settings.WHATSAPP_AGENT_ENABLED:
        logger.info("Agente deshabilitado (WHATSAPP_AGENT_ENABLED=false); mensaje de %s ignorado", telefono)
        return

    historial = _historial_reciente(telefono, limite=8)
    respuesta = generar_respuesta(telefono, texto, historial)
    ok, msg = enviar_mensaje(telefono, respuesta)
    if ok:
        _registrar_conversacion(telefono, "OUT", respuesta, origen="AGENTE")
    else:
        logger.error("No se pudo enviar respuesta a %s: %s", telefono, msg)


class _WebhookHandler(BaseHTTPRequestHandler):
    """Maneja GET (verificación) y POST (eventos) de Meta."""

    def log_message(self, format, *args) -> None:  # noqa: A002 (firma de BaseHTTPRequestHandler)
        logger.info("webhook: " + format, *args)

    def do_GET(self) -> None:
        if self.path.split("?")[0] != "/webhook":
            self.send_error(404)
            return
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(self.path).query)
        mode = qs.get("hub.mode", [""])[0]
        token = qs.get("hub.verify_token", [""])[0]
        challenge = qs.get("hub.challenge", [""])[0]

        if (
            mode == "subscribe"
            and settings.WHATSAPP_VERIFY_TOKEN
            and token == settings.WHATSAPP_VERIFY_TOKEN
        ):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            logger.info("Verificación de webhook aceptada")
        else:
            self.send_error(403, "Verify token inválido")

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/webhook":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)

        # Verificar firma antes de procesar nada
        firma = self.headers.get("X-Hub-Signature-256")
        if not verificar_firma(payload, firma):
            logger.warning("Firma de webhook inválida — evento rechazado")
            self.send_error(403, "Firma inválida")
            return

        try:
            data = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Payload no JSON: %s", e)
            self.send_error(400)
            return

        # Responder 200 inmediatamente (Meta reintenta si no recibe 200)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"received"}')

        mensajes = parsear_mensaje_entrante(data)
        for m in mensajes:
            try:
                _procesar_mensaje(m["telefono"], m["texto"])
            except Exception as e:
                logger.error(
                    "Error procesando mensaje de %s: %s", m["telefono"], e, exc_info=True
                )


def main() -> int:
    port = int(settings.WHATSAPP_WEBHOOK_PORT)
    server = ThreadingHTTPServer(("0.0.0.0", port), _WebhookHandler)
    logger.warning(
        "Servidor webhook WhatsApp escuchando en 0.0.0.0:%d — "
        "exponga este puerto con un túnel (Cloudflare Tunnel/ngrok)",
        port,
    )
    if not settings.WHATSAPP_AGENT_ENABLED:
        logger.warning(
            "WHATSAPP_AGENT_ENABLED=false — los mensajes se reciben pero NO se "
            "responden automáticamente. Active la variable para habilitar el agente."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.warning("Servidor webhook detenido")
        server.shutdown()
    return 0


if __name__ == "__main__":
    # Logging mínimo si se ejecuta standalone (sin main.py)
    import logging.handlers
    import os
    from pathlib import Path

    log_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "DELCA" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "whatsapp_webhook.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    import sys

    sys.exit(main())
