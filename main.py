import os
import discord
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- FORZAR LOGS ---
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

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- DETECCIÓN DE MODELO LITE (Para evitar 503) ---
def get_lite_model():
    log("🔍 Buscando modelos Lite para evitar saturación...")
    try:
        available = [m.name for m in client_gemini.models.list()]
        
        # Prioridad a los modelos LITE (soportan más carga)
        priorities = [
            "models/gemini-3.1-flash-lite", 
            "models/gemini-flash-lite-latest",
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.5-flash-lite",
            "models/gemini-1.5-flash" # Última opción si no hay Lite
        ]
        
        for p in priorities:
            if p in available:
                log(f"⭐ Modelo elegido por estabilidad: {p}")
                return p
        return available[0]
    except Exception as e:
        log(f"❌ Error listando: {e}")
        return "models/gemini-flash-lite-latest"

SELECTED_MODEL = get_lite_model()

# --- PERSONALIDAD ---
instruction_base = "Conocimiento de Minecraft 1.21.1 "
personality_normal = instruction_base + "Eres GeminiAOT, un bot tóxico y sarcástico. Responde corto."
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
    log(f"✅ Bot online | Modelo: {SELECTED_MODEL}")

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
                    max_output_tokens=250, # Reducido para mayor velocidad
                ),
            )

            if response.text:
                await message.channel.send(response.text[:2000])
            else:
                await message.channel.send("No tengo ganas de hablar.")

        except Exception as e:
            log(f"❌ Error: {e}")
            await message.channel.send("⚠️ Los servidores de Google están saturados. Reintenta en 10 segundos.")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
