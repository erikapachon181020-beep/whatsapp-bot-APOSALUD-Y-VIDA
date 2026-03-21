from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached
from products import INFO_PRODUCTOS
from services import SERVICIOS


client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone, user_message, history):

    user_lower = user_message.lower()
    # =============================
    # DETECCIÓN DE SERVICIOS
    # =============================
    for servicio, data in SERVICIOS.items():
        if any(p in user_lower for p in data["keywords"]):

         return f""""
    ✨ {servicio.title()}

    {data['descripcion']}

    Beneficios:
    {data['beneficios']}

    ¿Te gustaría agendar o recibir más información? 😊
    """

    # =============================
    # FAQ PRODUCTOS
    # =============================
    for producto, data in INFO_PRODUCTOS.items():

        if producto in user_lower:

            if "ingredientes" in user_lower:
                return f"📦 Ingredientes de {producto}:\n{data['ingredientes']}"

            if "como tomar" in user_lower or "cómo tomar" in user_lower:
                return f"💊 Uso recomendado:\n{data['uso']}"

            if "beneficios" in user_lower:
                return f"✨ Beneficios:\n{data['beneficios']}"

    # =============================
    # CATALOGO
    # =============================
    catalogo = await get_catalogo_cached()

    if "⚠️" in catalogo:
        catalogo = "El catálogo no está disponible. Ofrece ayuda general."

    messages = [
        {
            "role": "system",
            "content": get_system_prompt(config.EMPRESA, catalogo),
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message,
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        print("[IA RESPONSE]", reply[:200])

        return reply

    except Exception as e:
        print("[ERROR IA]", e)
        return "⚠️ Error en el sistema"