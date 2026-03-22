from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached
from products import INFO_PRODUCTOS
from services import SERVICIOS

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone, user_message, history, primer_mensaje=False):
    try:
        catalogo = get_catalogo_cached()

        system_prompt = get_system_prompt(config.EMPRESA, catalogo)

        # 🔥 FIX: evitar repetir saludo
        if not primer_mensaje:
            system_prompt += "\nIMPORTANTE: NO saludes nuevamente."

        messages = [{"role": "system", "content": system_prompt}]

        # historial
        for h in history[-6:]:
            messages.append({"role": "user", "content": h["user"]})
            messages.append({"role": "assistant", "content": h["assistant"]})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()

        print("[IA RESPONSE]", reply)

        return reply

    except Exception as e:
        print("[ERROR IA]", str(e))
        return "Ocurrió un problema, intenta nuevamente."
