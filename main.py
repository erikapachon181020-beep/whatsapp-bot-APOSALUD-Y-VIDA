from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode
from ai_engine import get_ai_response
from sheets import registrar_pedido

app = FastAPI()
twilio = Client(config.TWILIO_SID, config.TWILIO_TOKEN)


def send_whatsapp(to, body):
    twilio.messages.create(body=body, from_="whatsapp:" + config.TWILIO_NUMBER, to=to)


@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    try:
        history = get_history(phone)
        reply = await get_ai_response(phone, text, history)

        if "PEDIDO_CONFIRMAR" in reply:
            lines = reply.split("\n")
            idx = lines.index("PEDIDO_CONFIRMAR")

            nombre = lines[idx + 1]
            referencia = lines[idx + 2]
            producto = lines[idx + 3]
            presentacion = lines[idx + 4]
            marca = lines[idx + 5]
            sabor = lines[idx + 6]
            cantidad = int(lines[idx + 7])
            ubicacion = lines[idx + 8]
            precio = int(lines[idx + 9].replace("$", "").replace(".", ""))

            await registrar_pedido(
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

        save_messages(phone, text, reply)
        send_whatsapp(phone, reply)

    except Exception as e:
        print("[ERROR GENERAL]", e)
        send_whatsapp(phone, "⚠️ Error temporal, intenta de nuevo.")

    return PlainTextResponse("")
