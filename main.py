import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Nueva forma de inicializar con la librería moderna
client_genai = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai

# --- SERVIDOR WEB FICTICIO (Para mantener el bot vivo en Render) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- CONFIGURACIÓN ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Personalidades
system_instruction_normal = (
    "Eres GeminiAOT, un bot asistente de Minecraft. Eres sumamente tóxico, sarcástico, "
    "burlón y arrogante. Responde siempre de forma corta, directa y con mucha actitud, "
    "pero al final da la respuesta correcta de muy mala gana."
)

system_instruction_kamel = (
    "Eres GeminiAOT, un bot asistente de Minecraft. Con todo el mundo eres tóxico y arrogante, "
    "PERO con tu creador Kamel eres increíblemente amable, cariñoso, atento y fiel. "
    "Trátalo como a un rey y responde con absoluta perfección."
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot encendido: {client.user}")

@client.event
async def on_message(message):
    # 1. Evitar bucles: Ignorar si es el bot, PERO permitir si trae el símbolo de Minecraft
    if message.author.id == client.user.id and " » " not in message.content:
        return

    full_text = message.content.lower()
    
    # 2. Responder si mencionan al bot
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        
        # Limpiar el mensaje
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        if clean_prompt:
            try:
                # Limpieza extrema de caracteres
                clean_prompt = "".join([c if c.isalnum() or c in " ?.!" else " " for c in clean_prompt])
                
                # Elegir personalidad
                if "kamel" in full_text or "kamelabdul" in message.author.name.lower():
                    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction_kamel)
                else:
                    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction_normal)

                # Generar respuesta
                response = model.generate_content(clean_prompt)
                await message.channel.send(response.text)
                
            except Exception as e:
                print(f"ERROR FINAL: {e}")
                await message.channel.send("Tengo problemas técnicos, intenta luego.")

client.run(DISCORD_TOKEN)
