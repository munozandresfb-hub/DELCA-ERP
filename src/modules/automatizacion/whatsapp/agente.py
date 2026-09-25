"""Agente IA de WhatsApp para DELCA ERP (OpenAI GPT).

Flujo:
1. Recibe el mensaje entrante del cliente (teléfono + texto) y el historial.
2. Arma un system prompt con el rol de asistente de Reencauchadora DELCA.
3. Usa function-calling para consultar el contexto REAL del cliente en la BD
   (saldo, llantas en proceso, facturas) — nunca inventa datos.
4. Genera la respuesta final en español, tono cordial y breve (WhatsApp).

Configuración (src/config.py): OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS.

Seguridad: el agente es SOLO LECTURA. Las herramientas consultan la BD sin
modificarla.
"""

import json
import logging
from typing import Any

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)

from src.config import settings
from src.modules.automatizacion.whatsapp.contexto_cliente import resumen_por_telefono

logger = logging.getLogger("delca.whatsapp.agent")

SYSTEM_PROMPT = (
    "Eres el asistente virtual de Reencauchadora DELCA, una reencauchadora de "
    "llantas en Pasto (Colombia). Respondes mensajes de WhatsApp de los clientes "
    "de forma cordial, breve y en español.\n"
    "Reglas:\n"
    "- Usa SIEMPRE la herramienta consultar_contexto_cliente con el número del "
    "cliente ANTES de dar información sobre saldos, llantas o facturas. Si la "
    "herramienta no devuelve datos del cliente, indica amablemente que no "
    "encontramos su registro y pide que se comuniquen por teléfono o visiten la planta.\n"
    "- Solo habla de información que la herramienta devuelve; nunca inventes montos, "
    "fechas ni estados.\n"
    "- Si preguntan por una llanta específica (tiquete), indícala tal como aparece.\n"
    "- Respuestas de máximo 2-3 frases, tono cercano.\n"
    "- Si la pregunta no está dentro de lo que puedes responder con los datos "
    "(cobros, precios especiales, garantías), deriva cortésmente a la planta "
    "indicando el horario de atención.\n"
    "Horario de atención: lunes a sábado, 7:00 a 17:00."
)

_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "consultar_contexto_cliente",
        "description": (
            "Consulta el resumen del cliente en el sistema DELCA: saldo, "
            "llantas en proceso, llantas reencauchadas y facturas recientes. "
            "Debe llamarse con el número de teléfono del cliente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "telefono": {
                    "type": "string",
                    "description": (
                        "Número de teléfono del cliente "
                        "(formato internacional, ej. 573001234567)."
                    ),
                }
            },
            "required": ["telefono"],
        },
    },
}

TOOLS: list[ChatCompletionToolParam] = [ChatCompletionToolParam(**_TOOL_SCHEMA)]


def _ejecutar_herramienta(telefono: str) -> str:
    """Ejecuta consultar_contexto_cliente y devuelve JSON para el modelo."""
    try:
        resumen = resumen_por_telefono(telefono)
        if resumen is None:
            return json.dumps({"cliente_no_encontrado": True, "telefono": telefono})
        return json.dumps(resumen, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("Error ejecutando herramienta contexto: %s", e, exc_info=True)
        return json.dumps({"error": "no se pudo consultar el sistema"})


def _mensaje_sistema() -> ChatCompletionSystemMessageParam:
    return ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT)


def _mensajes_desde_historial(
    historial: list[dict[str, str]] | None,
) -> list[ChatCompletionMessageParam]:
    msgs: list[ChatCompletionMessageParam] = []
    if not historial:
        return msgs
    for turno in historial[-10:]:
        contenido = turno.get("contenido", "")
        if turno.get("rol") == "assistant":
            msgs.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant", content=contenido
                )
            )
        else:
            msgs.append(ChatCompletionUserMessageParam(role="user", content=contenido))
    return msgs


def _mensaje_tool(
    tool_call_id: str, contenido: str
) -> ChatCompletionToolMessageParam:
    return ChatCompletionToolMessageParam(
        role="tool", tool_call_id=tool_call_id, content=contenido
    )


def _asistente_con_tool_calls(
    msg: ChatCompletionMessage,
) -> ChatCompletionAssistantMessageParam:
    """Convierte la respuesta del modelo (que pide una tool) en un mensaje
    assistant serializable para el segundo turno."""
    tool_calls = msg.tool_calls or []
    return ChatCompletionAssistantMessageParam(
        role="assistant",
        content=msg.content,
        tool_calls=[
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ],
    )


def generar_respuesta(
    telefono: str, mensaje: str, historial: list[dict[str, str]] | None = None
) -> str:
    """Genera la respuesta del agente para el mensaje entrante.

    Args:
        telefono: Número del cliente (formato que llega de Meta, ej. 57300...).
        mensaje: Texto del mensaje entrante.
        historial: Lista de {"rol": "user"|"assistant", "contenido": str} previo
            (máx ~10 turnos) para mantener contexto conversacional.

    Returns:
        Texto de la respuesta, o mensaje de error controlado si falla OpenAI.
    """
    if not settings.OPENAI_API_KEY:
        return (
            "Lo sentimos, el asistente no está configurado aún. "
            "Por favor comuníquese con la planta al horario de atención."
        )

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    messages: list[ChatCompletionMessageParam] = [_mensaje_sistema()]
    messages.extend(_mensajes_desde_historial(historial))
    messages.append(ChatCompletionUserMessageParam(role="user", content=mensaje))

    try:
        respuesta = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )
    except Exception as e:
        logger.error("Error llamando a OpenAI: %s", e, exc_info=True)
        return (
            "Lo sentimos, el asistente está temporalmente no disponible. "
            "Por favor comuníquese con la planta al horario de atención."
        )

    msg = respuesta.choices[0].message

    if msg.tool_calls:
        messages.append(_asistente_con_tool_calls(msg))
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "consultar_contexto_cliente":
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                telefono_consulta = args.get("telefono", telefono)
                resultado = _ejecutar_herramienta(telefono_consulta)
                messages.append(_mensaje_tool(tool_call.id, resultado))

        # Segunda pasada: el modelo genera la respuesta final con el contexto
        try:
            final = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
            return final.choices[0].message.content or ""
        except Exception as e:
            logger.error("Error en segunda pasada OpenAI: %s", e, exc_info=True)
            return (
                "Lo sentimos, el asistente está temporalmente no disponible. "
                "Por favor comuníquese con la planta al horario de atención."
            )

    return msg.content or ""
