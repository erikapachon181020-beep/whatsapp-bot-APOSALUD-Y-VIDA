from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
    GROQ_KEY      = os.getenv("GROQ_API_KEY")
    SUPABASE_URL  = os.getenv("SUPABASE_URL")
    SUPABASE_KEY  = os.getenv("SUPABASE_KEY")
    EMPRESA       = os.getenv("EMPRESA_NOMBRE", "la empresa")
    MAX_HISTORIAL = int(os.getenv("MAX_HISTORIAL", "20"))
    PORT          = int(os.getenv("PORT", "8000"))

config = Config()