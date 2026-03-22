from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone: str, user_message: str, history: list) -> str:

    # Obtener catálogo
    try:
        catalogo = await get_catalogo()
    except:
        catalogo = "No disponible"

    # System prompt
    messages = [
        {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
    ]

    # Historial
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Mensaje usuario
    messages.append({"role": "user", "content": user_message})

    # Llamada a IA
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=500,
        temperature=0.5,  # 🔥 más control = menos locuras
    )

    return response.choices[0].message.content.strip()
