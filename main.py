import os
import discord
import threading
import sys # Para forzar los logs
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- FORZAR LOGS EN RENDER ---
def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot activo")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN GOOGLE GENAI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- DETECCIÓN DE MODELO ESTABLE (NO EXPERIMENTAL) ---
def get_stable_model():
    log("🔍 Buscando modelos estables...")
    try:
        available = [m.name for m in client_gemini.models.list()]
        log(f"📋 Modelos encontrados en tu cuenta: {available}")
        
        # Lista de prioridad: buscamos primero los estables, NO los 'exp'
        priorities = [
            "gemini-1.5-flash-8b", # Muy estable y rápido en 2026
            "gemini-1.5-flash", 
            "gemini-1.5-pro",
            "gemini-2.0-flash" 
        ]
        
        for p in priorities:
            if p in available:
                log(f"⭐ Elegido modelo estable: {p}")
                return p
        return available[0]
    except Exception as e:
        log(f"❌ Error listando modelos: {e}")
        return "gemini-1.5-flash-8b"

SELECTED_MODEL = get_stable_model()

# --- PERSONALIDAD ---
instruction_base = "Conocimiento total de Minecraft 1.21. "
personality_normal = instruction_base + "Eres GeminiAOT, un bot tóxico y sarcástico. Responde corto y directo."
personality_kamel = instruction_base + "Eres GeminiAOT. Con Kamel eres amable y fiel."

safety_config = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
]

# --- DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ Bot online | Usuario: {discord_client.user} | Modelo: {SELECTED_MODEL}")

@discord_client.event
async def on_message(message):
    if message.author.id == discord_client.user.id: return
    
    full_text = message.content.lower()
    if "geminiaot" in full_text or discord_client.user.mentioned_in(message):
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()
        
        if not clean_prompt: return

        try:
            is_kamel = "kamel" in full_text or "kamelabdul" in message.author.name.lower()
            sys_msg = personality_kamel if is_kamel else personality_normal

            response = client_gemini.models.generate_content(
                model=SELECTED_MODEL,
                contents=clean_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=safety_config,
                    max_output_tokens=300, # Reducido para evitar 503 por sobrecarga
                ),
            )

            if response.text:
                await message.channel.send(response.text[:2000])
            else:
                await message.channel.send("No tengo nada que decirte ahora mismo.")

        except Exception as e:
            log(f"❌ Error en respuesta: {e}")
            await message.channel.send(f"Error 503/404: `{str(e)[:100]}`. Intenta de nuevo en un momento.")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
