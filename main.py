import os
import discord
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types
from mcrcon import MCRcon # Nueva librería para Minecraft

# --- LOGS CONFIG ---
def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB PARA RENDER ---
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

# --- CONFIGURACIÓN APIS ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configuración RCON
RCON_IP = os.getenv("34.186.32.18")
RCON_PASS = os.getenv("16827131")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- SELECCIÓN DE MODELO ---
def get_working_model():
    log("🔍 Buscando modelos disponibles...")
    try:
        available = [m.name for m in client_gemini.models.list()]
        # Priorizamos Lite para evitar el error 503 de saturación
        priorities = ["models/gemini-3.1-flash-lite", "models/gemini-2.0-flash-lite", "models/gemini-1.5-flash"]
        for p in priorities:
            if p in available:
                log(f"⭐ Modelo seleccionado: {p}")
                return p
        return available[0]
    except Exception as e:
        log(f"❌ Error listando: {e}")
        return "models/gemini-3.1-flash-lite"

SELECTED_MODEL = get_working_model()

# --- PERSONALIDADES ---
instruction_base = "Conocimiento total de crafteo Minecraft 1.21. "
personality_normal = instruction_base + "Eres GeminiAOT, bot de Minecraft tóxico, sarcástico y arrogante. Responde corto y borde."
personality_kamel = instruction_base + "Eres GeminiAOT. Con Kamel eres amable, cariñoso y fiel. Es tu rey."

safety_config = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
]

# --- DISCORD BOT ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ Bot Online: {discord_client.user} | Modelo: {SELECTED_MODEL}")

@discord_client.event
async def on_message(message):
    # Ignorar mensajes propios
    if message.author.id == discord_client.user.id:
        return
    
    full_text = message.content.lower()
    
    # Detectar si nos hablan
    if "geminiaot" in full_text or discord_client.user.mentioned_in(message):
        # Limpiar el nombre del jugador y el prompt
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()
        
        if not clean_prompt: return

        try:
            # Seleccionar personalidad
            is_kamel = "kamel" in full_text or "kamelabdul" in message.author.name.lower()
            sys_msg = personality_kamel if is_kamel else personality_normal

            # Generar respuesta con Gemini
            response = client_gemini.models.generate_content(
                model=SELECTED_MODEL,
                contents=clean_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=safety_config,
                    max_output_tokens=300,
                ),
            )

            if response.text:
                respuesta_final = response.text[:2000]
                
                # 1. ENVIAR A DISCORD
                await message.channel.send(respuesta_final)
                log(f"✉️ Enviado a Discord: {respuesta_final}")

                # 2. ENVIAR A MINECRAFT VÍA RCON
                if RCON_IP and RCON_PASS:
                    try:
                        with MCRcon(RCON_IP, RCON_PASS, port=RCON_PORT) as mcr:
                            # Formateamos el mensaje para que se vea bien en Minecraft
                            # El comando 'say' es el más sencillo, 'tellraw' es para expertos
                            mcr.command(f'say [GeminiAOT] {respuesta_final}')
                            log("🎮 Retransmitido a Minecraft vía RCON")
                    except Exception as re:
                        log(f"⚠️ Error RCON: {re}")
                else:
                    log("⚠️ RCON no configurado. Solo se envió a Discord.")

        except Exception as e:
            log(f"❌ Error General: {e}")
            await message.channel.send("Tengo un problema en mi cerebro. Reintenta.")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
