from fastapi import APIRouter
from datetime import datetime, timedelta
from sheets import get_pedidos
from config import config
from twilio.rest import Client
import httpx
import json

router = APIRouter()

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)

APPS_SCRIPT_URL = "TU_SCRIPT_URL"


def send_whatsapp(to: str, body: str):
    try:
        twilio_client.messages.create(
            body=body,
            from_="whatsapp:" + config.TWILIO_NUMBER,
            to=to,
        )
    except Exception as e:
        print("[ERROR FOLLOWUP]", str(e))


async def marcar_followup(row_id, tipo):
    try:
        data = {
            "row_id": row_id,
            "tipo": tipo
        }

        async with httpx.AsyncClient() as client:
            await client.post(
                APPS_SCRIPT_URL,
                content=json.dumps(data),
                headers={"Content-Type": "application/json"},
            )
    except Exception as e:
        print("[ERROR UPDATE SHEET]", e)


@router.get("/followup")
async def followup():

    pedidos = await get_pedidos()

    for i, p in enumerate(pedidos):

        try:
            fecha = datetime.fromisoformat(p["fecha"])
            dias = int(p["dias_duracion"])
            telefono = p["telefono"]
            producto = p["producto"]

            ahora = datetime.now()

            # =============================
            # 🔥 DIA 3 (USO DEL PRODUCTO)
            # =============================
            if ahora >= fecha + timedelta(days=3) and not p.get("f3"):

                mensaje = (
                    f"Hola 👋 ¿Cómo vas con tu {producto}?\n\n"
                    "Recuerda tomarlo correctamente para mejores resultados 💪"
                )

                send_whatsapp(telefono, mensaje)
                await marcar_followup(i, "f3")

            # =============================
            # 🔥 CUANDO SE ACABA
            # =============================
            elif ahora >= fecha + timedelta(days=dias) and not p.get("f_final"):

                mensaje = (
                    f"Hola 😊 tu {producto} ya debe estar por terminarse.\n\n"
                    "Muchos clientes ya están haciendo su segundo pedido 👀\n"
                    "¿Quieres que te ayude a pedirlo de nuevo?"
                )

                send_whatsapp(telefono, mensaje)
                await marcar_followup(i, "f_final")

            # =============================
            # 🔥 RECORDATORIO FINAL
            # =============================
            elif ahora >= fecha + timedelta(days=dias + 3) and not p.get("f_extra"):

                mensaje = (
                    f"Hola 👋 no olvides continuar con tu {producto} para ver resultados.\n\n"
                    "Si quieres te ayudo a hacer tu pedido ahora mismo 😊"
                )

                send_whatsapp(telefono, mensaje)
                await marcar_followup(i, "f_extra")

        except Exception as e:
            print("[ERROR LOOP]", e)

    return {"ok": True}