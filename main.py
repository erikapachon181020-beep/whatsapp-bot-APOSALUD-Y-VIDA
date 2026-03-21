from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import uvicorn

from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode
from ai_engine import get_ai_response
from sheets import registrar_pedido
from products import INFO_PRODUCTOS, get_info
from followup import router as followup_router
from services import SERVICIOS

app = FastAPI(title="WhatsApp AI Bot APOSALUD")
app.include_router(followup_router)

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)

VENDEDOR = "whatsapp:+573226706141"


# =============================
# ENVÍO WHATSAPP
# =============================
def send_whatsapp(to: str, body: str, media_url: str = None):
    try:
        twilio_client.messages.create(
            body=body,
            from_="whatsapp:" + config.TWILIO_NUMBER,
            to=to,
            media_url=[media_url] if media_url else None,
        )
    except Exception as e:
        print("[ERROR TWILIO]", str(e))


# =============================
# HEALTH CHECK
# =============================
@app.get("/health")
def health_check():
    return {"status": "ok", "empresa": config.EMPRESA}


# =============================
# WEBHOOK
# =============================
@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    print(f"[MSG] {phone}: {text}")

    # =============================
    # COMANDOS ADMIN
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
        print("[HUMANO ACTIVO]")
        return PlainTextResponse("", status_code=200)

    # =============================
    # TRIGGER HUMANO
    # =============================
    if any(w in text.lower() for w in ["humano", "asesor", "agente"]):
        set_human_mode(phone, True)

        reply = "👨‍💼 Un asesor se comunicará contigo pronto."

        send_whatsapp(phone, reply)

        alerta = (
            "🚨 CLIENTE NECESITA ASESOR\n"
            f"Numero: {phone.replace('whatsapp:', '')}\n"
            f"Mensaje: {text}"
        )

        send_whatsapp(VENDEDOR, alerta)

        save_messages(phone, text, reply)

        return PlainTextResponse("", status_code=200)

    # =============================
    # IA RESPONSE
    # =============================
    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        print("[IA]", reply)

        # =============================
        # DETECTAR SERVICIOS
        # =============================
        for servicio, data in SERVICIOS.items():
            if servicio in reply.lower():
                send_whatsapp(phone, reply, data.get("imagen"))
                save_messages(phone, text, reply)
                return PlainTextResponse("", status_code=200)

        # =============================
        # PEDIDOS
        # =============================
        if "PEDIDO_CONFIRMAR" in reply:
            try:
                linea = [l for l in reply.split("\n") if "PEDIDO_CONFIRMAR" in l][0]
                partes = linea.split("|")

                nombre = partes[1].strip()
                referencia = partes[2].strip()
                producto = partes[3].strip()
                presentacion = partes[4].strip()
                sabor = partes[5].strip()
                cantidad = int(partes[6].strip())
                ubicacion = partes[7].strip()
                precio = int(partes[8].strip())

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
                        f"Cantidad: {cantidad}\n"
                        f"Total: ${total:,}\n\n"
                        "Un asesor te contactará pronto 😊"
                    )

            except Exception as e:
                print("[ERROR PEDIDO]", str(e))
                reply = "⚠️ Error procesando tu pedido. Un asesor te ayudará."

        # =============================
        # TRANSFERIR HUMANO
        # =============================
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)

            reply = "👨‍💼 Un asesor te contactará pronto."

            alerta = (
                "🚨 CLIENTE NECESITA ASESOR\n"
                f"Numero: {phone.replace('whatsapp:', '')}"
            )

            send_whatsapp(VENDEDOR, alerta)

        # =============================
        # DETECTAR PRODUCTO (IMÁGENES)
        # =============================
        info = None

        for producto in INFO_PRODUCTOS:
            if producto in reply.lower():
                info = get_info(producto)
                break

        # =============================
        # RESPUESTA FINAL
        # =============================
        save_messages(phone, text, reply)

        if info and info.get("imagen"):
            send_whatsapp(phone, reply, info["imagen"])
        else:
            send_whatsapp(phone, reply)

        print("[OK] Enviado a", phone)

    except Exception as e:
        print("[ERROR GENERAL]", str(e))
        send_whatsapp(phone, "⚠️ Error técnico. Intenta nuevamente.")

    return PlainTextResponse("", status_code=200)


# =============================
# RUN LOCAL
# =============================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT)