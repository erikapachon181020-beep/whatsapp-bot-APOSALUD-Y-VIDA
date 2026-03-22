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

app = FastAPI(title="WhatsApp AI Bot")
app.include_router(followup_router)

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)

VENDEDOR = "whatsapp:+573226706141"


def send_whatsapp(to: str, body: str, media_url: str = None):
    try:
        print("[ENVIANDO WHATSAPP]", to, body)

        twilio_client.messages.create(
            body=body,
            from_="whatsapp:" + config.TWILIO_NUMBER,
            to=to,
            media_url=[media_url] if media_url else None,
        )

    except Exception as e:
        print("[ERROR TWILIO]", str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text = Body.strip()

    print(f"[MSG] {phone}: {text}")

    if is_human_mode(phone):
        return PlainTextResponse("", status_code=200)

    try:
        history = get_history(phone)
        primer_mensaje = len(history) == 0

        reply = await get_ai_response(phone, text, history, primer_mensaje)

        # =============================
        # PEDIDO
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

                await registrar_pedido(
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

                reply = (
                    f"✅ Pedido confirmado\n\n"
                    f"{producto}\n"
                    f"{presentacion} | {sabor}\n"
                    f"Cantidad: {cantidad}\n"
                    f"Total: ${total:,}\n\n"
                    f"Te contactamos pronto."
                )

            except Exception as e:
                print("[ERROR PEDIDO]", e)
                reply = "⚠️ Error procesando pedido"

        save_messages(phone, text, reply)

        send_whatsapp(phone, reply)

    except Exception as e:
        print("[ERROR GENERAL]", str(e))
        send_whatsapp(phone, "Error técnico. Intenta luego.")

    return PlainTextResponse("", status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT)
