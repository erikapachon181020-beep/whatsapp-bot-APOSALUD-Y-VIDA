from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone: str, user_message: str, history: list) -> str:

    # Obtener catalogo actualizado de Google Sheets
    catalogo = await get_catalogo()
    print("[CATALOGO] " + str(len(catalogo)) + " chars — preview: " + catalogo[:150])

    # Bloquear si el catalogo no cargo correctamente
    if not catalogo or len(catalogo) < 50 or "No hay productos" in catalogo:
        return (
            "En este momento no puedo acceder al catálogo. "
            "Intenta en unos minutos o escribe 'asesor' para hablar con alguien."
        )

    # System prompt con catalogo incluido
    messages = [
        {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
    ]

    # Historial previo — solo pasar role y content, sin created_at ni otros campos
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Mensaje actual
    messages.append({"role": "user", "content": user_message})

    # Llamar a Groq
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=700,
        temperature=0.3,
    )

    return response.choices[0].message.content
