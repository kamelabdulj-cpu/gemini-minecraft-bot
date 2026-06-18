import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN DE APIS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Filtros de seguridad relajados para permitir la personalidad del bot
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- LÓGICA DE MODELO (CON FALLBACK) ---
# Intentaremos usar gemini-1.5-flash-latest que es el más compatible
MODEL_NAME = "gemini-1.5-flash-latest" 

instruction_base = "Conocimiento total de Minecraft 1.21. "
system_instruction_normal = instruction_base + "Eres GeminiAOT, un bot de Minecraft tóxico, sarcástico y arrogante. Corto y directo."
system_instruction_kamel = instruction_base + "Eres GeminiAOT. Con Kamel eres amable, cariñoso y fiel. Es tu rey."

def get_model(instruction):
    """Función para crear el modelo con el nombre correcto"""
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=instruction,
        safety_settings=safety_settings
    )

model_normal = get_model(system_instruction_normal)
model_kamel = get_model(system_instruction_kamel)

# --- DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot listo con modelo: {MODEL_NAME}")

@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    full_text = message.content.lower()
    
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        if not clean_prompt: return

        try:
            # Seleccionar personalidad
            selected_model = model_kamel if ("kamel" in full_text or "kamelabdul" in message.author.name.lower()) else model_normal
            
            # Generar respuesta
            response = selected_model.generate_content(clean_prompt)
            await message.channel.send(response.text[:2000])

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            
            # SI EL ERROR ES EL 404, INTENTAMOS CON OTRO NOMBRE DE MODELO AUTOMÁTICAMENTE
            if "404" in error_msg or "not found" in error_msg:
                await message.channel.send("⚠️ El modelo gemini-1.5-flash no responde. Intentando conectar con el respaldo...")
                try:
                    # Intento desesperado con el nombre genérico
                    fallback_model = genai.GenerativeModel("gemini-pro")
                    res = fallback_model.generate_content(clean_prompt)
                    await message.channel.send(res.text[:2000])
                except:
                    await message.channel.send("❌ Error crítico: Google no reconoce los modelos. Actualiza la librería en Render.")
            else:
                await message.channel.send(f"Error: `{error_msg[:100]}`")

if __name__ == "__m
