"""Servicio de WhatsApp Cloud API (Meta) para DELCA ERP.

Responsabilidades:
- Enviar mensajes de texto/plantillas vía Graph API.
- Verificar la firma X-Hub-Signature-256 de los webhooks entrantes.
- Parsear el payload de mensajes entrantes.

Configuración (variables de entorno, ver src/config.py):
  WHATSAPP_TOKEN       — token de acceso permanente (system user token)
  WHATSAPP_PHONE_ID    — phone_number_id del número verificado
  WHATSAPP_APP_SECRET  — app secret (firma del webhook)
  WHATSAPP_GRAPH_VERSION — versión de la Graph API (default v21.0)
"""

import hashlib
import hmac
import logging
from typing import Any

import requests

from src.config import settings

logger = logging.getLogger("delca.whatsapp")

GRAPH_BASE = "https://graph.facebook.com"


# ── Envío de mensajes ──────────────────────────────────────────────────

def enviar_mensaje(telefono: str, texto: str) -> tuple[bool, str]:
    """Envía un mensaje de texto al número (formato internacional, ej. 573001234567).

    Returns:
        (True, id_mensaje) si Meta aceptó el envío; (False, error) si no.
    """
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        return False, "WhatsApp no configurado (faltan WHATSAPP_TOKEN/WHATSAPP_PHONE_ID)"

    url = (
        f"{GRAPH_BASE}/{settings.WHATSAPP_GRAPH_VERSION}/"
        f"{settings.WHATSAPP_PHONE_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        logger.error("Error de red enviando WhatsApp a %s: %s", telefono, e)
        return False, f"Error de red: {e}"

    if resp.status_code == 200:
        data = resp.json()
        msg_id = (data.get("messages") or [{}])[0].get("id", "")
        logger.info("WhatsApp enviado a %s (id=%s)", telefono, msg_id)
        return True, msg_id

    logger.error(
        "Meta rechazó envío a %s: %s %s", telefono, resp.status_code, resp.text[:300]
    )
    return False, f"Meta {resp.status_code}: {resp.text[:200]}"


def enviar_plantilla(
    telefono: str, nombre_plantilla: str, componentes: list[dict[str, Any]] | None = None
) -> tuple[bool, str]:
    """Envía una plantilla aprobada (mensajes salientes a clientes que no
    escribieron primero requieren plantilla aprobada por Meta)."""
    url = (
        f"{GRAPH_BASE}/{settings.WHATSAPP_GRAPH_VERSION}/"
        f"{settings.WHATSAPP_PHONE_ID}/messages"
    )
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {"name": nombre_plantilla, "language": {"code": "es"}},
    }
    if componentes:
        payload["template"]["components"] = componentes

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        logger.error("Error de red enviando plantilla a %s: %s", telefono, e)
        return False, f"Error de red: {e}"

    if resp.status_code == 200:
        logger.info("Plantilla '%s' enviada a %s", nombre_plantilla, telefono)
        return True, resp.json().get("messages", [{}])[0].get("id", "")
    logger.error(
        "Meta rechazó plantilla a %s: %s %s", telefono, resp.status_code, resp.text[:300]
    )
    return False, f"Meta {resp.status_code}: {resp.text[:200]}"


# ── Verificación de firma del webhook ─────────────────────────────────

def verificar_firma(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Verifica la firma X-Hub-Signature-256 (HMAC-SHA256 del app_secret).

    Devuelve False si el header falta o la firma no coincide (rechazar el
    webhook). Usa hmac.compare_digest (a prueba de timing attacks).
    """
    if not settings.WHATSAPP_APP_SECRET or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, provided)


# ── Parseo de mensajes entrantes ──────────────────────────────────────

def parsear_mensaje_entrante(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae los mensajes entrantes del payload del webhook de Meta.

    Returns:
        Lista de dicts: {"telefono": str, "texto": str, "timestamp": str}.
        Vacío si el payload no contiene mensajes (ej. status updates).
    """
    mensajes: list[dict[str, Any]] = []
    entries = payload.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue  # ignorar imágenes, botones, etc. (v1: solo texto)
                texto = (msg.get("text") or {}).get("body", "")
                if not texto:
                    continue
                mensajes.append({
                    "telefono": msg.get("from", ""),
                    "texto": texto,
                    "timestamp": str(msg.get("timestamp", "")),
                })
    return mensajes