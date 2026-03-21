from supabase import create_client
from config import config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def get_history(phone: str) -> list:
    """Obtiene los ultimos N mensajes de un usuario """
    result = (supabase.table("conversations")
        .select("role,content")
        .eq("phone", phone)
        .order("created_at", desc=False)
        .limit(config.MAX_HISTORIAL)
        .execute())
    return result.data or []

def save_messages(phone: str, user_msg: str, bot_reply: str): 
    """Guarda el mensaje del usuario y la respuesta del bot"""
    supabase.table("conversations").insert([
        {"phone": phone, "role": "user",      "content": user_msg},
        {"phone": phone, "role": "assistant", "content": bot_reply},
    ]).execute()

def is_human_mode(phone: str) -> bool:
    """"Verifica si el usuario esta en modo atencion humano"""
    r = (supabase.table("users")
         .select("is_human")
         .eq("phone", phone)
         .execute())
    return r.data[0].get("is_human", False) if r.data else False

def set_human_mode(phone: str, active: bool):
    """Activa o desactiva el modo atencion humana"""
    supabase.table("users").upsert(
        {"phone": phone, "is_human": active}
    ).execute()