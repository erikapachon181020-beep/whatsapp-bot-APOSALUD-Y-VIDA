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


def send_whatsapp(to, body):
    twilio_client.messages.create(
        body=body, from_="whatsapp:" + config.TWILIO_NUMBER, to=to
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "bot": config.EMPRESA}


@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    print("[MSG] " + phone + ": " + text)

    # =============================
    # 🔄 CONTROL HUMANO
    # =============================
    if text.startswith("/bot-on"):
        numero = text.split(" ")[1]
        numero = "whatsapp:" + numero if not numero.startswith("whatsapp:") else numero
        set_human_mode(numero, False)
        send_whatsapp(phone, "Bot reactivado")
        return PlainTextResponse("", status_code=200)

    if text.startswith("/bot-off"):
        numero = text.split(" ")[1]
        numero = "whatsapp:" + numero if not numero.startswith("whatsapp:") else numero
        set_human_mode(numero, True)
        send_whatsapp(phone, "Bot desactivado")
        return PlainTextResponse("", status_code=200)

    if is_human_mode(phone):
        print("[HUMANO ACTIVO]")
        return PlainTextResponse("", status_code=200)

    # =============================
    # 🔥 PEDIR ASESOR
    # =============================
    if any(w in text.lower() for w in ["asesor", "humano", "agente"]):
        set_human_mode(phone, True)

        send_whatsapp(phone, "Te conecto con un asesor en unos minutos 🙌")

        alerta = (
            "🚨 CLIENTE NECESITA ASESOR\n\n"
            f"Numero: {phone.replace('whatsapp:', '')}\n"
            f"Mensaje: {text}\n\n"
            "Cuando termines escribe:\n"
            f"/bot-on {phone.replace('whatsapp:', '')}"
        )

        send_whatsapp(VENDEDOR, alerta)
        return PlainTextResponse("", status_code=200)

    # =============================
    # 🤖 IA
    # =============================
    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        # =============================
        # 🔥 TRANSFERIR HUMANO DESDE IA
        # =============================
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)

            send_whatsapp(phone, "Te conecto con un asesor 🙌")

            send_whatsapp(VENDEDOR, f"🚨 CLIENTE REQUIERE ASESOR\n{phone}")

            return PlainTextResponse("", status_code=200)

        # =============================
        # 🧾 PROCESAR PEDIDO
        # =============================
        if "PEDIDO_CONFIRMAR" in reply:

            linea = ""
            for l in reply.split("\n"):
                if l.startswith("PEDIDO_CONFIRMAR"):
                    linea = l.strip()
                    break

            print("[PEDIDO DETECTADO]", linea)

            try:
                partes = linea.split("|")

                nombre = partes[1]
                referencia = partes[2]
                producto = partes[3]
                presentacion = partes[4]
                marca = partes[5]
                sabor = partes[6]
                cantidad = int(partes[7])
                ubicacion = partes[8]

                precio_raw = (
                    partes[9].replace("$", "").replace(".", "").replace(",", "")
                )
                precio = int(precio_raw)

                ok = await registrar_pedido(
                    telefono=phone.replace("whatsapp:", ""),
                    nombre=nombre,
                    referencia=referencia,
                    producto=producto,
                    presentacion=presentacion,
                    marca=marca,
                    sabor=sabor,
                    cantidad=cantidad,
                    precio=precio,
                    ubicacion=ubicacion,
                )

                if ok:
                    reply = (
                        "✅ Pedido registrado correctamente\n\n"
                        "Un asesor te escribirá para confirmar 🙌"
                    )

                    send_whatsapp(VENDEDOR, f"🛒 NUEVO PEDIDO\n{nombre} - {producto}")

                else:
                    reply = "⚠️ Error guardando el pedido, un asesor te contactará."

            except Exception as e:
                print("[ERROR PEDIDO]", str(e))
                reply = "⚠️ Error procesando pedido, te contactamos."

        # =============================
        # 💾 GUARDAR HISTORIAL
        # =============================
        save_messages(phone, text, reply)

        # =============================
        # 📲 RESPUESTA FINAL
        # =============================
        send_whatsapp(phone, reply)

    except Exception as e:
        print("[ERROR GENERAL]", str(e))
        send_whatsapp(phone, "Error técnico, intenta en un momento.")

    return PlainTextResponse("", status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT)
