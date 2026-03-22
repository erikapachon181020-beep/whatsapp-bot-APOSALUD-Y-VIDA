from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(phone, user_message, history):
    catalogo = await get_catalogo_cached()

    messages = [
        {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
    ]

    for msg in history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=700,
    )

    return response.choices[0].message.content
