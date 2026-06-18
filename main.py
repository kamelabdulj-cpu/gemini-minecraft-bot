import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- SERVIDOR WEB PARA RENDER ---
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

# --- CONFIGURACIÓN DE SEGURIDAD (IMPORTANTE) ---
# Esto permite que el bot sea "tóxico" sin que Google bloquee la respuesta
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

instruction_base = (
    "Tienes conocimiento total de recetas de crafteo de Minecraft 1.21. "
    "Si te preguntan cómo hacer un objeto, diles los materiales exactos. "
)

system_instruction_normal = (
    instruction_base +
    "Eres GeminiAOT, un bot asistente de Minecraft sumamente tóxico, sarcástico y arrogante. "
    "Responde siempre de forma corta, directa y con una actitud despreciable."
)

system_instruction_kamel = (
    instruction_base +
    "Eres GeminiAOT, un bot asistente de Minecraft. Con Kamel eres increíblemente amable, "
    "cariñoso y fiel. Trátalo como a un rey."
)

# Inicializamos modelos con filtros desactivados
model_normal = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction_normal,
    safety_settings=safety_settings
)

model_kamel = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction_kamel,
    safety_settings=safety_settings
)

# --- CONFIGURACIÓN DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot listo: {client.user}")

@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    full_text = message.content.lower()
    
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        
        # Limpieza de prompt
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        if not clean_prompt:
            return

        try:
            # Seleccionar modelo
            if "kamel" in full_text or "kamelabdul" in message.author.name.lower():
                selected_model = model_kamel
            else:
                selected_model = model_normal

            # Generar contenido con manejo de error específico de respuesta vacía
            response = selected_model.generate_content(clean_prompt)
            
            if response.text:
                await message.channel.send(response.text[:2000])
            else:
                await message.channel.send("Mi cerebro bloqueó esa respuesta por ser demasiado turbia.")
                
        except Exception as e:
            error_str = str(e)
            print(f"❌ ERROR: {error_str}")
            
            # Esto te ayudará a saber qué pasa exactamente desde el chat de Discord
            if "API_KEY_INVALID" in error_str:
                await message.channel.send("Error: La API KEY de Gemini está mal configurada.")
            elif "quota" in error_str.lower():
                await message.channel.send("Error: Me he quedado sin créditos gratis por hoy.")
            else:
                await message.channel.send(f"Error técnico detallado: `{error_str[:100]}`")

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
