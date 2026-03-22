from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from ai_engine import get_ai_response

app = FastAPI()

# Memoria simple
chat_history = {}


@app.post("/webhook")
async def whatsapp_webhook(request: Request):

    form = await request.form()

    user_message = form.get("Body", "").strip()
    phone = form.get("From", "")

    if not user_message:
        return Response(content=str(MessagingResponse()), media_type="application/xml")

    # Historial por usuario
    if phone not in chat_history:
        chat_history[phone] = []

    history = chat_history[phone]

    try:
        ai_reply = await get_ai_response(phone, user_message, history)

    except Exception as e:
        print("ERROR IA:", e)
        ai_reply = "Disculpa, tuve un problema técnico. Intenta de nuevo 🙏"

    # Guardar historial
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_reply})

    # Limitar memoria
    chat_history[phone] = history[-10:]

    # Respuesta a Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(ai_reply)

    return Response(content=str(twilio_response), media_type="application/xml")
