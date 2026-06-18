import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot activo")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# 1. BUSCAR MODELO DISPONIBLE AUTOMÁTICAMENTE
print("🔍 Buscando modelos disponibles...")
available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
print(f"✅ Modelos encontrados: {available_models}")

# Prioridad de modelos para 2026
preferred_models = [
    'models/gemini-1.5-flash', 
    'models/gemini-1.5-flash-latest', 
    'models/gemini-2.0-flash', # Posible modelo en 2026
    'models/gemini-1.5-pro'
]

SELECTED_MODEL = next((m for m in preferred_models if m in available_models), available_models[0])
print(f"🚀 Usando el modelo: {SELECTED_MODEL}")

# --- PERSONALIDAD ---
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
}

instruction_base = "Conocimiento de Minecraft 1.21. "
system_instruction_normal = instruction_base + "Eres GeminiAOT, un bot tóxico, sarcástico y arrogante. Responde corto."
system_instruction_kamel = instruction_base + "Eres GeminiAOT. Con Kamel eres amable y fiel."

# Crear modelos
try:
    model_normal = genai.GenerativeModel(model_name=SELECTED_MODEL, system_instruction=system_instruction_normal, safety_settings=safety_settings)
    model_kamel = genai.GenerativeModel(model_name=SELECTED_MODEL, system_instruction=system_instruction_kamel, safety_settings=safety_settings)
except Exception as e:
    print(f"⚠️ Error con system_instruction, intentando modo compatible: {e}")
    model_normal = genai.GenerativeModel(model_name=SELECTED_MODEL)
    model_kamel = genai.GenerativeModel(model_name=SELECTED_MODEL)

# --- DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot online: {client.user} | Modelo: {SELECTED_MODEL}")

@client.event
async def on_message(message):
    if message.author.id == client.user.id: return
    
    full_text = message.content.lower()
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()
        
        if not clean_prompt: return

        try:
            model = model_kamel if ("kamel" in full_text or "kamelabdul" in message.author.name.lower()) else model_normal
            response = model.generate_content(clean_prompt)
            await message.channel.send(response.text[:2000])
        except Exception as e:
            print(f"❌ Error: {e}")
            await message.channel.send(f"Error técnico: `{str(e)[:100]}`")

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
