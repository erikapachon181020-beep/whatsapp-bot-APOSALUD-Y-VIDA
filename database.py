from supabase import create_client
from config import config
from datetime import datetime, date

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


def get_history(phone: str) -> list:
    result = (supabase.table("conversations")
        .select("role,content,created_at")
        .eq("phone", phone)
        .order("created_at", desc=False)
        .limit(config.MAX_HISTORIAL)
        .execute())
    return result.data or []


def save_messages(phone: str, user_msg: str, bot_reply: str):
    supabase.table("conversations").insert([
        {"phone": phone, "role": "user",      "content": user_msg},
        {"phone": phone, "role": "assistant", "content": bot_reply},
    ]).execute()


def clear_history(phone: str):
    """Borra el historial de conversacion de un usuario."""
    try:
        supabase.table("conversations").delete().eq("phone", phone).execute()
        print("[HISTORIAL] Borrado para " + phone)
    except Exception as e:
        print("[ERROR CLEAR HISTORY] " + str(e))


def is_new_session(phone: str) -> bool:
    """
    Retorna True si el usuario no ha hablado hoy.
    Se usa para limpiar historial viejo y empezar sesion limpia.
    """
    try:
        result = (supabase.table("conversations")
            .select("created_at")
            .eq("phone", phone)
            .order("created_at", desc=True)
            .limit(1)
            .execute())

        if not result.data:
            return True  # Nunca ha escrito antes

        last_msg = result.data[0]["created_at"]
        last_date = datetime.fromisoformat(last_msg[:10]).date()
        today = date.today()

        return last_date < today  # True si el ultimo mensaje fue antes de hoy
    except Exception as e:
        print("[ERROR SESSION CHECK] " + str(e))
        return False


def is_human_mode(phone: str) -> bool:
    r = (supabase.table("users")
         .select("is_human")
         .eq("phone", phone)
         .execute())
    return r.data[0].get("is_human", False) if r.data else False


def set_human_mode(phone: str, active: bool):
    supabase.table("users").upsert(
        {"phone": phone, "is_human": active}
    ).execute()
