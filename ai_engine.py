from groq import Groq
from config import config
from prompts import get_system_prompt
from sheets import get_catalogo_cached  # 🔥 usamos cache para evitar latencia

client = Groq(api_key=config.GROQ_KEY)


async def get_ai_response(
    phone: str, user_message: str, history: list, primer_mensaje: bool = False
) -> str:
    try:
        # =============================
        # 📦 CATALOGO
        # =============================
        catalogo = await get_catalogo_cached()

        # =============================
        # 🧠 SYSTEM PROMPT
        # =============================
        messages = [
            {"role": "system", "content": get_system_prompt(config.EMPRESA, catalogo)}
        ]

        # =============================
        # 🧾 HISTORIAL
        # =============================
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # =============================
        # 👋 CONTROL DE SALUDO (ANTI-SPAM)
        # =============================
        texto = user_message.lower().strip()

        es_saludo = any(
            s in texto
            for s in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"]
        )

        # 🔥 SOLO saluda si es el PRIMER mensaje
        if primer_mensaje and es_saludo:
            messages.append(
                {
                    "role": "user",
                    "content": "El usuario acaba de iniciar conversación diciendo hola. Responde con saludo de bienvenida y ofrece productos.",
                }
            )
        else:
            messages.append({"role": "user", "content": user_message})

        # =============================
        # 🤖 GROQ
        # =============================
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.6,
        )

        reply = response.choices[0].message.content.strip()

        # =============================
        # 🧼 LIMPIEZA BÁSICA
        # =============================
        if not reply:
            return "Hola 👋 ¿En qué producto estás interesado?"

        return reply

    except Exception as e:
        print("[ERROR AI_ENGINE]", str(e))
        return "⚠️ Error generando respuesta. Intenta nuevamente."
