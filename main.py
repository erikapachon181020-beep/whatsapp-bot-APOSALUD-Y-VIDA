from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import uvicorn

from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode
from ai_engine import get_ai_response
from sheets import registrar_pedido

app = FastAPI(title="WhatsApp AI Bot")
twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)

VENDEDOR = "whatsapp:+573226706141"


# =============================
# 📲 ENVIAR WHATSAPP
# =============================
def send_whatsapp(to, body):
    twilio_client.messages.create(
        body=body, from_="whatsapp:" + config.TWILIO_NUMBER, to=to
    )


# =============================
# ❤️ HEALTH CHECK
# =============================
@app.get("/health")
def health_check():
    return {"status": "ok", "bot": config.EMPRESA}


# =============================
# 🔥 WEBHOOK TWILIO
# =============================
@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):

    phone = From
    text = Body.strip()

    print("[MSG]", phone, ":", text)

    # =============================
    # 🔧 COMANDOS ADMIN
    # =============================
    if text.startswith("/bot-on"):
        numero = text.split(" ")[-1]
        if not numero.startswith("whatsapp:"):
            numero = "whatsapp:" + numero

        set_human_mode(numero, False)
        send_whatsapp(phone, "Bot reactivado ✅")
        return PlainTextResponse("", status_code=200)

    if text.startswith("/bot-off"):
        numero = text.split(" ")[-1]
        if not numero.startswith("whatsapp:"):
            numero = "whatsapp:" + numero

        set_human_mode(numero, True)
        send_whatsapp(phone, "Bot desactivado ❌")
        return PlainTextResponse("", status_code=200)

    # =============================
    # 👨‍💼 MODO HUMANO
    # =============================
    if is_human_mode(phone):
        print("[HUMANO ACTIVO]", phone)
        return PlainTextResponse("", status_code=200)

    # =============================
    # 🧠 DETECTAR ASESOR
    # =============================
    if any(w in text.lower() for w in ["asesor", "humano", "agente"]):
        set_human_mode(phone, True)

        reply = "Un asesor se comunicará contigo pronto 🙌"
        send_whatsapp(phone, reply)

        alerta = (
            "🚨 CLIENTE NECESITA ASESOR\n\n"
            "Número: " + phone.replace("whatsapp:", "") + "\n"
            "Mensaje: " + text
        )
        send_whatsapp(VENDEDOR, alerta)

        save_messages(phone, text, reply)
        return PlainTextResponse("", status_code=200)

    # =============================
    # 🤖 IA
    # =============================
    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        # =============================
        # 🔥 PEDIDO
        # =============================
        if "PEDIDO_CONFIRMAR" in reply:

            linea = ""
            for l in reply.split("\n"):
                if "PEDIDO_CONFIRMAR" in l:
                    linea = l.strip()
                    break

            print("[PEDIDO DETECTADO]", linea)

            try:
                partes = linea.split("|")

                nombre = partes[1].strip()
                referencia = partes[2].strip()
                producto = partes[3].strip()
                presentacion = partes[4].strip()
                marca = partes[5].strip()
                sabor = partes[6].strip()
                cantidad = int(partes[7].strip())
                ubicacion = partes[8].strip()

                precio_raw = (
                    partes[9].strip().replace("$", "").replace(".", "").replace(",", "")
                )
                precio = int(precio_raw)

                total = cantidad * precio

                ok = await registrar_pedido(
                    phone,
                    nombre,
                    referencia,
                    producto,
                    presentacion,
                    marca,
                    sabor,
                    cantidad,
                    precio,
                    ubicacion,
                )

                if ok:
                    reply = (
                        "✅ *Pedido confirmado*\n\n"
                        f"🛍 Producto: {producto}\n"
                        f"📦 Presentación: {presentacion}\n"
                        f"🔢 Cantidad: {cantidad}\n"
                        f"💰 Total: ${total:,}".replace(",", ".") + "\n\n"
                        "Un asesor te contactará para finalizar la entrega 🙌"
                    )
                else:
                    reply = "❌ Error registrando pedido. Un asesor te ayudará."

            except Exception as e:
                print("[ERROR PARSE]", e)
                reply = "❌ No pude procesar el pedido. Un asesor te escribirá."

        # =============================
        # 💾 GUARDAR Y RESPONDER
        # =============================
        save_messages(phone, text, reply)
        send_whatsapp(phone, reply)

        print("[OK RESPUESTA]", phone)

    except Exception as e:
        print("[ERROR GENERAL]", str(e))
        send_whatsapp(phone, "⚠️ Error temporal, intenta de nuevo.")

    return PlainTextResponse("", status_code=200)


# =============================
# 🚀 RUN
# =============================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
