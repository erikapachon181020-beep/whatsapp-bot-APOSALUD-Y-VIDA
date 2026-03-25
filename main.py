from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import uvicorn
import re

from config import config
from database import get_history, save_messages, is_human_mode, set_human_mode, clear_history, is_new_session
from ai_engine import get_ai_response
from sheets import registrar_pedido
from followup import router as followup_router

app = FastAPI(title="WhatsApp AI Bot — APOSALUD Y VIDA")
app.include_router(followup_router)

twilio_client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)

VENDEDOR = "whatsapp:+573226706141"  # Numero del asesor principal


def send_whatsapp(to: str, body: str):
    twilio_client.messages.create(
        body=body,
        from_="whatsapp:" + config.TWILIO_NUMBER,
        to=to
    )


def parse_pedido(reply: str):
    """
    Busca y parsea la linea PEDIDO_CONFIRMAR en la respuesta del bot.
    Retorna un dict con los campos o None si no se puede parsear.
    """
    for linea in reply.split("\n"):
        linea = linea.strip()
        if not linea.startswith("PEDIDO_CONFIRMAR"):
            continue

        print("[PEDIDO LINEA RAW] " + linea)

        # Limpiar caracteres raros que el modelo pueda agregar
        linea = re.sub(r"[*_`]", "", linea).strip()
        partes = [p.strip() for p in linea.split("|")]

        if len(partes) < 10:
            print("[ERROR PARSE] Solo " + str(len(partes)) + " partes, se esperaban 10")
            return None

        try:
            precio_raw = partes[9].replace("$", "").replace(".", "").replace(",", "").strip()
            precio = int(precio_raw)
        except ValueError:
            print("[ERROR PARSE] Precio invalido: " + partes[9])
            return None

        return {
            "nombre":       partes[1],
            "referencia":   partes[2],
            "producto":     partes[3],
            "presentacion": partes[4],
            "marca":        partes[5],
            "sabor":        partes[6],
            "cantidad":     partes[7],
            "ubicacion":    partes[8],
            "precio":       precio,
        }

    return None


@app.get("/health")
def health_check():
    return {"status": "ok", "bot": config.EMPRESA}


@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    phone = From
    text  = Body.strip()
    print("[MSG] " + phone + ": " + text)

    # ── Comandos del vendedor ──────────────────────────────────────
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

    # Comando para limpiar historial manualmente (util para debug)
    if text.startswith("/reset"):
        partes = text.split(" ")
        numero = partes[1].strip() if len(partes) == 2 else phone
        if not numero.startswith("whatsapp:"):
            numero = "whatsapp:" + numero
        clear_history(numero)
        send_whatsapp(phone, "Historial borrado para " + numero)
        return PlainTextResponse("", status_code=200)

    # ── Modo humano activo ─────────────────────────────────────────
    if is_human_mode(phone):
        print("[HUMANO] " + phone + " bot desactivado")
        return PlainTextResponse("", status_code=200)

    # ── Nueva sesion: limpiar historial del dia anterior ──────────
    if is_new_session(phone):
        print("[NUEVA SESION] Limpiando historial de " + phone)
        clear_history(phone)

    # ── Palabras clave para transferir a asesor ────────────────────
    triggers = ["humano", "asesor", "persona", "agente"]
    if any(w in text.lower() for w in triggers):
        set_human_mode(phone, True)
        reply = "Un asesor se comunicara contigo pronto. Horario: Lun-Sab 9am-7pm."
        send_whatsapp(phone, reply)
        save_messages(phone, text, reply)
        alerta = ("CLIENTE NECESITA ASESOR\n"
                  "Numero: " + phone.replace("whatsapp:", "") + "\n"
                  "Mensaje: " + text + "\n\n"
                  "Cuando termines escribe:\n"
                  "/bot-on " + phone.replace("whatsapp:", ""))
        send_whatsapp(VENDEDOR, alerta)
        return PlainTextResponse("", status_code=200)

    # ── Flujo principal IA ─────────────────────────────────────────
    try:
        history = get_history(phone)
        reply   = await get_ai_response(phone, text, history)

        # Transferencia a humano detectada por la IA
        if "TRANSFERIR_HUMANO" in reply:
            set_human_mode(phone, True)
            reply = "No tengo esa informacion. Un asesor te contactara pronto."
            alerta = ("CLIENTE NECESITA ASESOR\n"
                      "Numero: " + phone.replace("whatsapp:", "") + "\n"
                      "Cuando termines escribe:\n"
                      "/bot-on " + phone.replace("whatsapp:", ""))
            send_whatsapp(VENDEDOR, alerta)

        # Pedido detectado
        elif "PEDIDO_CONFIRMAR" in reply:
            pedido = parse_pedido(reply)

            if pedido is None:
                print("[ERROR PEDIDO] No se pudo parsear la linea tecnica")
                reply = "Hubo un problema procesando tu pedido. Un asesor te ayudara pronto."
                alerta = ("PEDIDO FALLIDO — REQUIERE ATENCION MANUAL\n"
                          "Numero: " + phone.replace("whatsapp:", "") + "\n"
                          "El bot no pudo parsear el pedido correctamente.")
                send_whatsapp(VENDEDOR, alerta)
            else:
                try:
                    cantidad = int(pedido["cantidad"])
                except ValueError:
                    cantidad = 1

                total = cantidad * pedido["precio"]

                ok = await registrar_pedido(
                    phone,
                    pedido["nombre"],
                    pedido["referencia"],
                    pedido["producto"],
                    pedido["presentacion"],
                    pedido["marca"],
                    pedido["sabor"],
                    cantidad,
                    pedido["precio"],
                    pedido["ubicacion"],
                )

                if ok:
                    reply = ("Pedido registrado exitosamente. ✅\n"
                             "Producto: "     + pedido["producto"]     + "\n"
                             "Presentacion: " + pedido["presentacion"] + "\n"
                             "Marca: "        + pedido["marca"]        + " | Sabor: " + pedido["sabor"] + "\n"
                             "Cantidad: "     + str(cantidad)          + "\n"
                             "Ubicacion: "    + pedido["ubicacion"]    + "\n"
                             "Total: $"       + "{:,}".format(total).replace(",", ".") + "\n\n"
                             "Un asesor te confirmara el pedido pronto.")
                else:
                    reply = "Hubo un problema registrando tu pedido. Un asesor te ayudara pronto."
                    alerta = ("PEDIDO FALLIDO — ERROR EN SHEETS\n"
                              "Numero: " + phone.replace("whatsapp:", "") + "\n"
                              "Cliente: " + pedido["nombre"] + "\n"
                              "Producto: " + pedido["producto"])
                    send_whatsapp(VENDEDOR, alerta)

        save_messages(phone, text, reply)
        send_whatsapp(phone, reply)
        print("[OK] Respuesta enviada a " + phone)

    except Exception as e:
        print("[ERROR] " + str(e))
        send_whatsapp(phone, "Tuve un problema tecnico. Intenta en unos minutos.")

    return PlainTextResponse("", status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
