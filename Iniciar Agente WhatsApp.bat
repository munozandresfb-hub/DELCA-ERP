@echo off
rem Agente WhatsApp - usa la ruta de esta carpeta (portable)
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m src.modules.automatizacion.whatsapp.servidor_webhook
