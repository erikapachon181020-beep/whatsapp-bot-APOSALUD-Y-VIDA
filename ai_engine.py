from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone: str, user_message: str, history: list) -> str:

    try:
        # 📦 catálogo dinámico
        catalogo = await get_catalogo()
    except:
        catalogo = ""

    messages = [
        {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
    ]

    # 🧠 historial
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # 👤 mensaje actual
    messages.append({"role": "user", "content": user_message})

    # 🤖 IA
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()
