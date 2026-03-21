from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import uvicorn
import logging

from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode
from ai_engine import get_ai_response
from sheets import registrar_pedido
from products import INFO_PRODUCTOS, get_info
from followup import router as followup_router
from services import SERVICIOS

# =============================
# CONFIG LOGS
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp AI Bot")
app.include_router(followup_router)

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)
VENDEDOR = "whatsapp:+573226706141"


# =============================
# UTILIDAD WHATSAPP
# =============================
def send_whatsapp(to: str, body: str, media_url: str = None):
    try:
        twilio_client.messages.create(
            body=body,
            from_=f"whatsapp:{config.TWILIO_NUMBER}",
            to=to,
            media_url=[media_url] if media_url else None,
        )
    except Exception as e:
        logger.error(f"[TWILIO ERROR] {e}")


# =============================
# HEALTH CHECK
# =============================
@app.get("/health")
def health_check():
    return {"status": "ok", "bot": config.EMPRESA}


# =============================
# WEBHOOK PRINCIPAL
# =============================
@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    logger.info(f"[MSG] {phone}: {text}")

    # =============================
    # COMANDOS
    # =============================
    if text.startswith("/bot-on"):
        set_human_mode(phone, False)
        send_whatsapp(phone, "✅ Bot activado")
        return PlainTextResponse("", status_code=200)

    if text.startswith("/bot-off"):
        set_human_mode(phone, True)
        send_whatsapp(phone, "⛔ Bot desactivado")
        return PlainTextResponse("", status_code=200)

    # =============================
    # MODO HUMANO
    # =============================
    if is_human_mode(phone):
        logger.info("[HUMANO ACTIVO]")
        return PlainTextResponse("", status_code=200)

    # =============================
    # TRIGGER HUMANO
    # =============================
    if any(w in text.lower() for w in ["humano", "asesor", "agente"]):
        set_human_mode(phone, True)

        reply = "Un asesor se comunicará contigo pronto 👨‍💼"
        send_whatsapp(phone, reply)

        alerta = (
            "🚨 CLIENTE NECESITA ASESOR\n"
            f"Número: {phone.replace('whatsapp:', '')}\n"
            f"Mensaje: {text}"
        )
        send_whatsapp(VENDEDOR, alerta)

        save_messages(phone, text, reply)
        return PlainTextResponse("", status_code=200)

    # =============================
    # IA
    # =============================
    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        # =============================
        # TRANSFERENCIA HUMANO
        # =============================
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)

            reply = "No tengo esa información. Un asesor te contactará pronto."

            alerta = (
                "🚨 CLIENTE NECESITA ASESOR\n"
                f"Número: {phone.replace('whatsapp:', '')}"
            )
            send_whatsapp(VENDEDOR, alerta)

        # =============================
        # PEDIDOS (ROBUSTO)
        # =============================
        elif "PEDIDO_CONFIRMAR" in reply:
            try:
                linea = next(
                    (l for l in reply.split("\n") if "PEDIDO_CONFIRMAR" in l),
                    None,
                )

                if not linea:
                    raise ValueError("Formato de pedido inválido")

                partes = linea.split("|")

                if len(partes) < 9:
                    raise ValueError("Datos incompletos en pedido")

                nombre = partes[1].strip()
                referencia = partes[2].strip()
                producto = partes[3].strip()
                presentacion = partes[4].strip()
                sabor = partes[5].strip()
                cantidad = int(partes[6])
                ubicacion = partes[7].strip()
                precio = int(partes[8])

                total = cantidad * precio

                ok = await registrar_pedido(
                    phone,
                    nombre,
                    referencia,
                    producto,
                    presentacion,
                    sabor,
                    cantidad,
                    precio,
                    ubicacion,
                )

                if ok:
                    reply = (
                        "✅ Pedido confirmado\n\n"
                        f"Producto: {producto}\n"
                        f"Presentación: {presentacion}\n"
                        f"Sabor: {sabor}\n"
                        f"Cantidad: {cantidad}\n"
                        f"Total: ${total:,}\n\n"
                        "Un asesor te contactará pronto."
                    )
                else:
                    reply = "⚠️ No se pudo registrar el pedido"

            except Exception as e:
                logger.error(f"[ERROR PEDIDO] {e}")
                reply = "⚠️ Error procesando tu pedido. Intenta nuevamente."

        # =============================
        # IMÁGENES AUTOMÁTICAS
        # =============================
        media_url = None

        # Servicios
        for servicio in SERVICIOS:
            if servicio in reply.lower():
                media_url = SERVICIOS[servicio].get("imagen")
                break

        # Productos
        if not media_url:
            for producto in INFO_PRODUCTOS:
                if producto in reply.lower():
                    info = get_info(producto)
                    if info and info.get("imagen"):
                        media_url = info["imagen"]
                        break

        # =============================
        # RESPUESTA FINAL
        # =============================
        save_messages(phone, text, reply)
        send_whatsapp(phone, reply, media_url)

        logger.info(f"[OK] Enviado a {phone}")

    except Exception as e:
        logger.error(f"[ERROR GENERAL] {e}")
        send_whatsapp(
            phone,
            "Tuve un problema técnico. Intenta en unos minutos."
        )

    return PlainTextResponse("", status_code=200)


# =============================
# RUN
# =============================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT)