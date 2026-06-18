import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- SERVIDOR WEB (Corregido para Render) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot activo")
    def do_HEAD(self): # Esto evita el error 501 que salía en tus logs
        self.send_response(200); self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN NUEVA SDK 2026 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Inicializamos el nuevo cliente de Google
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# Configuración de comportamiento
instruction_base = "Conocimiento total de Minecraft 1.21. "
personality_normal = instruction_base + "Eres GeminiAOT, un bot de Minecraft sumamente tóxico, sarcástico y arrogante. Responde corto y con odio."
personality_kamel = instruction_base + "Eres GeminiAOT. Con Kamel eres increíblemente amable, cariñoso y fiel. Es tu rey."

# Configuración de Seguridad (Para que permita ser tóxico)
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
    print(f"✅ Bot GeminiAOT (Versión 2026) listo: {discord_client.user}")

@discord_client.event
async def on_message(message):
    if message.author.id == discord_client.user.id: return
    
    full_text = message.content.lower()
    
    if "geminiaot" in full_text or discord_client.user.mentioned_in(message):
        # Limpiar prompt
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()
        
        if not clean_prompt: return

        try:
            # Seleccionar instrucción de sistema según el usuario
            is_kamel = "kamel" in full_text or "kamelabdul" in message.author.name.lower()
            sys_msg = personality_kamel if is_kamel else personality_normal

            # Llamada a la NUEVA API (google.genai)
            # Usamos gemini-1.5-flash que es el estándar actual
            response = client_gemini.models.generate_content(
                model="gemini-1.5-flash",
                contents=clean_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=safety_config,
                    max_output_tokens=500,
                ),
            )

            if response.text:
                await message.channel.send(response.text[:2000])
            else:
                await message.channel.send("No tengo ganas de responderte eso.")

        except Exception as e:
            print(f"❌ Error API: {e}")
            await message.channel.send(f"Error técnico 2026: `{str(e)[:100]}`")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
