import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

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

# --- CONFIGURACIÓN GOOGLE GENAI 2026 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- DETECCIÓN AUTOMÁTICA DE MODELO ---
def get_working_model():
    print("🔍 Buscando modelos disponibles en tu cuenta...")
    try:
        # Listamos los modelos y buscamos el más moderno disponible (2.0 o 1.5)
        available = [m.name for m in client_gemini.models.list()]
        print(f"📋 Modelos encontrados: {available}")
        
        # Prioridad de nombres para 2026
        priorities = ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-flash"]
        
        for p in priorities:
            if p in available:
                return p
        return available[0] # Si no encuentra ninguno de la lista, usa el primero que vea
    except Exception as e:
        print(f"❌ Error listando modelos: {e}")
        return "gemini-1.5-flash" # Fallback por si falla la lista

SELECTED_MODEL = get_working_model()
print(f"🚀 Bot configurado para usar: {SELECTED_MODEL}")

# --- PERSONALIDAD ---
instruction_base = "Conocimiento total de Minecraft 1.21. "
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
    print(f"✅ Bot online | Modelo: {SELECTED_MODEL}")

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
                model=SELECTED_MODEL, # Usamos el detectado automáticamente
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
                await message.channel.send("No tengo nada que decirte.")

        except Exception as e:
            print(f"❌ Error: {e}")
            await message.channel.send(f"Error técnico 404/429: `{str(e)[:80]}...` \n*Tip: Revisa los logs de Render para ver qué modelos tienes disponibles.*")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
