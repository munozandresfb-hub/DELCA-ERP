# Integración WhatsApp + Agente IA — Guía de Configuración

**Sistema:** DELCA ERP · **Módulo:** `src/modules/automatizacion/whatsapp/` (dentro del módulo Automatización)
**Fecha:** 23/09/2026 · **Estado:** código implementado y verificado (194 tests, smoke webhook PASS)

---

## 1. Qué quedó implementado

| Componente | Archivo | Función |
|---|---|---|
| Servicio Cloud API | `src/modules/automatizacion/whatsapp/whatsapp_service.py` | Enviar texto/plantillas, verificar firma, parsear mensajes |
| Contexto del cliente | `src/modules/automatizacion/whatsapp/contexto_cliente.py` | Busca cliente por teléfono, saldo, llantas en proceso, facturas (BD real) |
| Agente IA | `src/modules/automatizacion/whatsapp/agente.py` | OpenAI GPT con function-calling: responde con datos reales del cliente |
| Servidor webhook | `src/modules/automatizacion/whatsapp/servidor_webhook.py` | Recibe eventos de Meta (GET verificación, POST mensajes) |
| Historial | tabla `whatsapp_conversaciones` | Guarda la conversación (contexto para el agente) |
| Arranque | `Iniciar Agente WhatsApp.bat` | Lanza el webhook con pythonw |

**Flujo:** cliente escribe a WhatsApp → Meta envía POST al webhook → firma verificada → agente consulta la BD (saldo/llantas del cliente) → responde por la Cloud API → se guarda en historial.

---

## 2. Configuración requerida (3 pasos externos que debes hacer tú)

### Paso 1 — Crear la app en Meta (15 min)
1. Entra a [developers.facebook.com](https://developers.facebook.com) con la cuenta de la empresa.
2. Crear app → tipo **Business** → añadir producto **WhatsApp**.
3. En **WhatsApp → API Setup**: obtener el **phone_number_id** (aparece junto al número) y un **token temporal** para probar.
4. En **WhatsApp → Configuration**: 
   - **Callback URL** → la URL pública del webhook (ver Paso 3)
   - **Verify token** → inventa uno, ej. `delca_webhook_2026`
   - **Webhook fields** → suscribirse a `messages`
5. En **Settings → Basic**: copiar el **App secret**.
6. **Importante:** para token permanente, crear un **System User** (Settings → Advanced → System User) con permiso `whatsapp_business_messaging` y generar token de acceso largo plazo.

### Paso 2 — Activar OpenAI (5 min)
1. [platform.openai.com](https://platform.openai.com) → API keys → crear una clave `sk-...`.
2. (Opcional) Verificar que el modelo `gpt-4o-mini` está disponible en tu cuenta.

### Paso 3 — Exponer el webhook públicamente (10 min)
El PC del taller no tiene IP pública. Se usa un túnel (el más simple: Cloudflare Tunnel, gratis):

**Con Cloudflare Tunnel:**
1. Instalar `cloudflared` (winget install cloudflare/cloudflared).
2. Crear túnel hacia el puerto local:
   ```
   cloudflared tunnel --url http://localhost:9090
   ```
3. Te da una URL tipo `https://xxx.trycloudflare.com` — esa es la **Callback URL** de Meta.

**Con ngrok (alternativa):**
```
ngrok http 9090
```
Da una URL `https://xxx.ngrok.io`.

---

## 3. Configurar el `.env` del proyecto

Editar `Programacion DELCA v2\.env` (copiar los valores obtenidos):

```ini
WHATSAPP_TOKEN=EAAG...token_largo_plazo
WHATSAPP_PHONE_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=delca_webhook_2026
WHATSAPP_APP_SECRET=app_secret_de_meta
WHATSAPP_GRAPH_VERSION=v21.0
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=300
WHATSAPP_AGENT_ENABLED=false
WHATSAPP_WEBHOOK_PORT=9090
```

> **Seguridad:** activar `WHATSAPP_AGENT_ENABLED=true` SOLO después de probar con `false` (modo seguro: recibe y registra sin responder). Revisar logs `%LOCALAPPDATA%\DELCA\logs\whatsapp_webhook.log`.

---

## 4. Puesta en marcha

```bat
:: 1) Iniciar el webhook (en el PC del taller)
"Iniciar Agente WhatsApp.bat"
:: o manualmente:
.venv\Scripts\python.exe -m src.modules.automatizacion.whatsapp.servidor_webhook

:: 2) Probar envío manual
.venv\Scripts\python.exe -c "from src.modules.whatsapp import enviar_mensaje; print(enviar_mensaje('573001234567', 'Prueba DELCA'))"

:: 3) Verificar logs
:: %LOCALAPPDATA%\DELCA\logs\whatsapp_webhook.log
```

---

## 5. Verificación realizada (ya probado)

- ✅ 194 tests pasan (14 nuevos del módulo WhatsApp)
- ✅ Smoke webhook: GET verificación → challenge ✓ · token malo → 403 ✓ · POST firma válida → 200 ✓ · firma inválida → 403 ✓
- ✅ Contexto real: cliente "María Jose Delgado Castillo" encontrado por teléfono `3147461848` → saldo/llantas/facturas consultados de la BD
- ✅ Tabla `whatsapp_conversaciones` creada en la BD de producción
- ✅ basedpyright: 0 errores en los módulos nuevos

---

## 6. Notas y limitaciones

- **Plantillas:** los mensajes salientes a clientes que NO escribieron primero requieren plantilla aprobada por Meta (la función `enviar_plantilla` está lista; el agente responde dentro de la ventana de 24h sin plantilla).
- **Costos:** OpenAI por tokens (~centavos por conversación corta) + Meta por conversación iniciada por el negocio (~USD 0.02-0.05).
- **Privacidad:** el agente envía resumen del cliente (saldo, llantas) a OpenAI — si se prefiere 100% local, migrar a Ollama (cambiar solo `agente.py`).
- **El agente es SOLO LECTURA** de la BD: responde con datos reales, nunca modifica nada.
- **Solo texto** por ahora (v1): imágenes/audio se ignoran.

---

## 7. Extensión futura (cuando quieras)

- **Notificaciones automáticas**: al cambiar estado de llanta / quedar saldo → `enviar_plantilla` con datos del evento (disparadores desde los servicios existentes).
- **Webhook como servicio Windows**: registrar `servidor_webhook.py` como tarea programada o servicio (NSSM) para que arranque solo.
- **Soporte de imágenes/audio** en el agente (v2).
