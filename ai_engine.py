from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(
    phone: str, user_message: str, history: list, primer_mensaje: bool
) -> str:

    try:
        # =============================
        # CATALOGO (CACHE)
        # =============================
        catalogo = await get_catalogo_cached()

        # =============================
        # SYSTEM PROMPT
        # =============================
        messages = [
            {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
        ]

        # =============================
        # HISTORIAL (limitado)
        # =============================
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # =============================
        # MENSAJE ACTUAL
        # =============================
        messages.append({"role": "user", "content": user_message})

        # =============================
        # GROQ
        # =============================
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=400,
            temperature=0.5,
        )

        reply = response.choices[0].message.content

        print("[IA OK]", reply)

        return reply

    except Exception as e:
        print("[ERROR IA]", str(e))
        return "Estoy teniendo problemas técnicos 😔"
