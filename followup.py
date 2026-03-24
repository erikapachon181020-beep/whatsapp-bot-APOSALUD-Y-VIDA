from fastapi import APIRouter
from datetime import datetime, timedelta
from twilio.rest import Client
from config import config
from sheets import get_pedidos

router = APIRouter()

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)


def send_whatsapp(to: str, body: str):
    try:
        twilio_client.messages.create(
            body=body,
            from_="whatsapp:" + config.TWILIO_NUMBER,
            to=to
        )
    except Exception as e:
        print("[ERROR FOLLOWUP] " + str(e))


@router.get("/followup")
async def followup():
    pedidos = await get_pedidos()

    for p in pedidos:
        try:
            fecha    = datetime.fromisoformat(p["fecha"])
            dias     = int(p["dias_duracion"])
            telefono = p["telefono"]
            producto = p["producto"]
            ahora    = datetime.now()

            # DIA 3 — Recordatorio de uso
            if ahora >= fecha + timedelta(days=3) and not p.get("f3"):
                mensaje = ("Hola como vas con tu " + producto + "?\n\n"
                           "Recuerda tomarlo correctamente para mejores resultados.")
                send_whatsapp(telefono, mensaje)

            # CUANDO SE ACABA — Oferta de recompra
            elif ahora >= fecha + timedelta(days=dias) and not p.get("f_final"):
                mensaje = ("Hola, tu " + producto + " ya debe estar por terminarse.\n\n"
                           "Muchos clientes ya estan haciendo su segundo pedido.\n"
                           "Quieres que te ayude a pedirlo de nuevo?")
                send_whatsapp(telefono, mensaje)

            # RECORDATORIO EXTRA — 3 dias despues
            elif ahora >= fecha + timedelta(days=dias + 3) and not p.get("f_extra"):
                mensaje = ("Hola, no olvides continuar con tu " + producto + " para ver resultados.\n\n"
                           "Si quieres te ayudo a hacer tu pedido ahora mismo.")
                send_whatsapp(telefono, mensaje)

        except Exception as e:
            print("[ERROR LOOP FOLLOWUP] " + str(e))

    return {"ok": True}
