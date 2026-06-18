import os
import discord
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types
from mcrcon import MCRcon

# --- FORZAR LOGS PARA RENDER ---
def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB DUMMY (Mantiene vivo el bot en Render) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot GeminiAOT Activo")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN DE DATOS (IP Y CLAVE) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Datos de tu servidor Minecraft
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

# Inicializar IA
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- DETECCIÓN AUTOMÁTICA DE MODELO ---
def get_working_model():
    log("🔍 Buscando modelos disponibles...")
    try:
        available = [m.name for m in client_gemini.models.list()]
        # Priorizamos el 3.1-flash-lite que vimos en tus logs por ser el más estable
        priorities = ["models/gemini-3.1-flash-lite", "models/gemini-2.0-flash-lite", "models/gemini-1.5-flash"]
        for p in priorities:
            if p in available:
                log(f"⭐ Modelo seleccionado: {p}")
                return p
        return "models/gemini-3.1-flash-lite"
    except Exception as e:
        log(f"❌ Error listando modelos: {e}")
        return "models/gemini-3.1-flash-lite"

SELECTED_MODEL = get_working_model()

# --- PERSONALIDADES ---
instruction_base = "Conocimiento total de crafteo Minecraft 1.21. "
personality_normal = instruction_base + "Eres GeminiAOT, bot de Minecraft tóxico, sarcástico y arrogante. Responde siempre corto y borde."
personality_kamel = instruction_base + "Eres GeminiAOT. Con tu creador Kamel eres increíblemente amable, cariñoso y fiel. Trátalo como a un rey."

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
    log(f"✅ Bot Online: {discord_client.user} | Usando: {SELECTED_MODEL}")

@discord_client.event
async def on_message(message):
    # No responderse a sí mismo
    if message.author.id == discord_client.user.id:
        return
    
    full_text = message.content.lower()
    
    # Detectar si alguien menciona al bot
    if "geminiaot" in full_text or discord_client.user.mentioned_in(message):
        
        # Limpiar el texto si viene de un puente (Jugador » mensaje)
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()
        
        if not clean_prompt:
            return

        try:
            # Seleccionar personalidad
            is_kamel = "kamel" in full_text or "kamelabdul" in message.author.name.lower()
            sys_msg = personality_kamel if is_kamel else personality_normal

            # Obtener respuesta de la IA
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
                texto_ia = response.text[:2000]
                
                # 1. Enviar a Discord
                await message.channel.send(texto_ia)
                log(f"✉️ Discord: {texto_ia}")

                # 2. Enviar a Minecraft vía RCON
                try:
                    with MCRcon(RCON_IP, RCON_PASS, port=RCON_PORT, timeout=5) as mcr:
                        # Usamos el comando 'say' para que salga en el chat global
                        mcr.command(f'say [GeminiAOT] {texto_ia}')
                        log("🎮 Minecraft: Enviado con éxito.")
                except Exception as re:
                    log(f"⚠️ Error RCON (¿Puerto abierto?): {re}")
            
        except Exception as e:
            log(f"❌ Error General: {e}")
            await message.channel.send("Mi cerebro se sobrecalentó. Intenta de nuevo.")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
