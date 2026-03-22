from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(
    phone: str, user_message: str, history: list, primer_mensaje: bool = False
) -> str:
    try:
        # =============================
        # 📦 CATALOGO (CACHE)
        # =============================
        try:
            catalogo = await get_catalogo_cached()
        except:
            catalogo = "Catálogo no disponible"

        # =============================
        # 🧠 SYSTEM PROMPT
        # =============================
        messages = [
            {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
        ]

        # =============================
        # 🧾 HISTORIAL (LIMITADO)
        # =============================
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # =============================
        # 👋 CONTROL SALUDO
        # =============================
        texto = user_message.lower().strip()

        es_saludo = any(
            s in texto
            for s in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"]
        )

        if primer_mensaje and es_saludo:
            messages.append(
                {
                    "role": "user",
                    "content": "El usuario inicia conversación. Saluda y ofrece productos.",
                }
            )
        else:
            messages.append({"role": "user", "content": user_message})

        # =============================
        # 🛒 DETECCIÓN DE COMPRA
        # =============================
        if any(x in texto for x in ["comprar", "lo quiero", "quiero", "me interesa"]):
            messages.append(
                {
                    "role": "system",
                    "content": "El usuario quiere comprar. NO ofrezcas más productos. Solicita datos para cerrar venta.",
                }
            )

        # =============================
        # 🤖 GROQ
        # =============================
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=300,
            temperature=0.5,
        )

        reply = response.choices[0].message.content.strip()

        if not reply:
            return "Hola 👋 ¿En qué producto estás interesado?"

        return reply

    except Exception as e:
        print("[ERROR AI_ENGINE]", str(e))
        return "⚠️ Error generando respuesta. Intenta nuevamente."
