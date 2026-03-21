from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import uvicorn

from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode
from ai_engine import get_ai_response
from sheets import registrar_pedido
from products import INFO_PRODUCTOS, get_info
from followup import router as followup_router  # 👈 NUEVO
from services import SERVICIOS

app = FastAPI()
app.include_router(followup_router)

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)


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


@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    print(f"[MSG] {phone}: {text}")

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
        print("[HUMANO ACTIVO]")
        return PlainTextResponse("", status_code=200)

    # =============================
    # TRIGGER HUMANO
    # =============================
    if any(w in text.lower() for w in ["humano", "asesor", "agente"]):
        set_human_mode(phone, True)
        send_whatsapp(phone, "Te conecto con un asesor 👨‍💼")
        return PlainTextResponse("", status_code=200)

    # =============================
    # IA
    # =============================
    history = get_history(phone)
    reply = await get_ai_response(phone, text, history)
    # =============================
    # DETECTAR SERVICIOS
    # ============================
    for servicio in SERVICIOS:
        if servicio in reply.lower():
             send_whatsapp(phone, reply, SERVICIOS[servicio]["imagen"])
    return PlainTextResponse("", status_code=200)

    # =============================
    # PEDIDOS
    # =============================
    if "PEDIDO_CONFIRMAR" in reply:
        try:
            linea = [l for l in reply.split("\n") if "PEDIDO_CONFIRMAR" in l][0]
            partes = linea.split("|")

            nombre = partes[1]
            referencia = partes[2]
            producto = partes[3]
            presentacion = partes[4]
            sabor = partes[5]
            cantidad = int(partes[6])
            ubicacion = partes[7]
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
                    f"Cantidad: {cantidad}\n"
                    f"Total: ${total:,}\n\n"
                    "Un asesor te contactará pronto."
                )

        except Exception as e:
            print("[ERROR PEDIDO]", e)
            reply = "⚠️ Error procesando pedido"

    # =============================
    # TRANSFERENCIA HUMANO
    # =============================
    if "TRANSFERIR_HUMANO" in reply:
        set_human_mode(phone, True)
        reply = "Te paso con un asesor 👨‍💼"

    # =============================
    # 🔥 DETECTAR PRODUCTO Y ENVIAR IMAGEN
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

    return PlainTextResponse("", status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT)