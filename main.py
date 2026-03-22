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
# 🔍 HEALTH CHECK
# =============================
@app.get("/health")
def health_check():
    return {"status": "ok", "bot": config.EMPRESA}


# =============================
# 📩 WEBHOOK TWILIO
# =============================
@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    print("[MSG]", phone, ":", text)

    # =============================
    # 🔄 ACTIVAR / DESACTIVAR BOT
    # =============================
    if text.startswith("/bot-on"):
        numero = text.split(" ")[-1]
        if not numero.startswith("whatsapp:"):
            numero = "whatsapp:" + numero

        set_human_mode(numero, False)
        send_whatsapp(phone, "Bot reactivado correctamente ✅")
        return PlainTextResponse("", status_code=200)

    if text.startswith("/bot-off"):
        numero = text.split(" ")[-1]
        if not numero.startswith("whatsapp:"):
            numero = "whatsapp:" + numero

        set_human_mode(numero, True)
        send_whatsapp(phone, "Bot desactivado. Atención humana activa 👨‍💼")
        return PlainTextResponse("", status_code=200)

    # =============================
    # 👤 MODO HUMANO ACTIVO
    # =============================
    if is_human_mode(phone):
        print("[HUMANO ACTIVO]", phone)
        return PlainTextResponse("", status_code=200)

    # =============================
    # 🧠 DETECTAR SOLICITUD DE ASESOR
    # =============================
    triggers = ["humano", "asesor", "persona", "agente"]

    if any(w in text.lower() for w in triggers):
        set_human_mode(phone, True)

        reply = "Un asesor se comunicará contigo en breve 🤝"
        send_whatsapp(phone, reply)

        alerta = (
            "🚨 CLIENTE SOLICITA ASESOR\n\n"
            f"📞 Número: {phone.replace('whatsapp:', '')}\n"
            f"💬 Mensaje: {text}\n\n"
            "Cuando termines escribe:\n"
            f"/bot-on {phone.replace('whatsapp:', '')}"
        )

        send_whatsapp(VENDEDOR, alerta)
        save_messages(phone, text, reply)

        return PlainTextResponse("", status_code=200)

    # =============================
    # 🤖 RESPUESTA IA
    # =============================
    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        # =============================
        # 🔁 TRANSFERIR A HUMANO
        # =============================
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)

            reply = "Un asesor te contactará pronto 🤝"

            alerta = (
                "🚨 CLIENTE REQUIERE ASESOR\n\n"
                f"📞 Número: {phone.replace('whatsapp:', '')}\n\n"
                "Para reactivar bot:\n"
                f"/bot-on {phone.replace('whatsapp:', '')}"
            )

            send_whatsapp(VENDEDOR, alerta)

        # =============================
        # 🧾 PROCESAR PEDIDO
        # =============================
        elif "PEDIDO_CONFIRMAR" in reply:

            linea = ""
            for l in reply.split("\n"):
                if "PEDIDO_CONFIRMAR" in l:
                    linea = l.strip()
                    break

            print("[PEDIDO DETECTADO]", linea)

            partes = linea.split("|")
            exito = False

            try:
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
                    ubicacion,
                    precio,
                )

                if ok:
                    reply = (
                        "🧾 *Pedido registrado con éxito*\n\n"
                        f"📦 Producto: {producto}\n"
                        f"📋 Presentación: {presentacion}\n"
                        f"🏷 Marca: {marca}\n"
                        f"🍓 Sabor: {sabor}\n"
                        f"🔢 Cantidad: {cantidad}\n"
                        f"📍 Ubicación: {ubicacion}\n"
                        f"💰 Total: ${total:,}".replace(",", ".")
                        + "\n\nUn asesor te confirmará el pedido en breve 🤝"
                    )

                    # 🔔 ALERTA AL VENDEDOR
                    alerta = (
                        "🛒 NUEVO PEDIDO\n\n"
                        f"Cliente: {nombre}\n"
                        f"Tel: {phone.replace('whatsapp:', '')}\n\n"
                        f"Producto: {producto}\n"
                        f"Presentación: {presentacion}\n"
                        f"Marca: {marca}\n"
                        f"Sabor: {sabor}\n"
                        f"Cantidad: {cantidad}\n"
                        f"Ubicación: {ubicacion}\n\n"
                        f"💰 Total: ${total:,}".replace(",", ".")
                    )

                    send_whatsapp(VENDEDOR, alerta)

                    # 🔁 ACTIVAR MODO HUMANO
                    set_human_mode(phone, True)

                    exito = True

            except Exception as ep:
                print("[ERROR PARSE]", str(ep))

            if not exito:
                reply = "Hubo un problema con tu pedido. Un asesor te ayudará 🤝"

        # =============================
        # 💾 GUARDAR Y RESPONDER
        # =============================
        save_messages(phone, text, reply)
        send_whatsapp(phone, reply)

        print("[OK] Respuesta enviada a", phone)

    except Exception as e:
        print("[ERROR GENERAL]", str(e))
        send_whatsapp(phone, "Error temporal. Intenta en unos minutos 🙏")

    return PlainTextResponse("", status_code=200)


# =============================
# 🚀 RUN LOCAL
# =============================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
