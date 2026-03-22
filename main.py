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
    # 🔁 ACTIVAR / DESACTIVAR BOT
    # =============================
    if text.startswith("/bot-on"):
        partes = text.split(" ")
        if len(partes) == 2:
            numero = partes[1].strip()
            if not numero.startswith("whatsapp:"):
                numero = "whatsapp:" + numero
            set_human_mode(numero, False)
            send_whatsapp(phone, "Bot reactivado para " + numero)
            return PlainTextResponse("", status_code=200)

    if text.startswith("/bot-off"):
        partes = text.split(" ")
        if len(partes) == 2:
            numero = partes[1].strip()
            if not numero.startswith("whatsapp:"):
                numero = "whatsapp:" + numero
            set_human_mode(numero, True)
            send_whatsapp(phone, "Bot desactivado para " + numero)
            return PlainTextResponse("", status_code=200)

    # =============================
    # 🧍 MODO HUMANO
    # =============================
    if is_human_mode(phone):
        print("[HUMANO] " + phone + " bot desactivado")
        return PlainTextResponse("", status_code=200)

    triggers = ["humano", "asesor", "persona", "agente"]
    if any(w in text.lower() for w in triggers):
        set_human_mode(phone, True)
        reply = "Un asesor se comunicará contigo pronto 🤝"
        send_whatsapp(phone, reply)

        save_messages(phone, text, reply)

        alerta = (
            "🚨 CLIENTE NECESITA ASESOR\n"
            "Número: " + phone.replace("whatsapp:", "") + "\n"
            "Mensaje: " + text + "\n\n"
            "Cuando termines escribe:\n"
            "/bot-on " + phone.replace("whatsapp:", "")
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
        # 👤 TRANSFERENCIA
        # =============================
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)
            reply = "Te conectaré con un asesor para ayudarte mejor 🤝"

            alerta = (
                "🚨 CLIENTE NECESITA ASESOR\n"
                "Número: " + phone.replace("whatsapp:", "") + "\n\n"
                "Cuando termines escribe:\n"
                "/bot-on " + phone.replace("whatsapp:", "")
            )
            send_whatsapp(VENDEDOR, alerta)

        # =============================
        # 🧾 PEDIDO
        # =============================
        elif "PEDIDO_CONFIRMAR" in reply:

            linea = ""
            for l in reply.split("\n"):
                if "PEDIDO_CONFIRMAR" in l:
                    linea = l.strip()
                    break

            print("[PEDIDO LINEA] " + linea)

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
                        "✅ Pedido registrado exitosamente\n\n"
                        "Producto: " + producto + "\n"
                        "Presentación: " + presentacion + "\n"
                        "Marca: " + marca + "\n"
                        "Sabor: " + sabor + "\n"
                        "Cantidad: " + str(cantidad) + "\n"
                        "Total: $" + "{:,}".format(total).replace(",", ".") + "\n\n"
                        "Un asesor te confirmará el pedido en breve 🤝"
                    )
                    exito = True

            except Exception as ep:
                print("[ERROR PARSE] " + str(ep))

            if not exito:
                reply = "Hubo un problema procesando tu pedido. Un asesor te ayudará 🤝"

        # =============================
        # 💾 GUARDAR HISTORIAL
        # =============================
        save_messages(phone, text, reply)
        send_whatsapp(phone, reply)

        print("[OK] Respuesta enviada a " + phone)

    except Exception as e:
        print("[ERROR] " + str(e))
        send_whatsapp(phone, "Tuve un problema técnico. Intenta en unos minutos.")

    return PlainTextResponse("", status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
