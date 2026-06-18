import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai

# --- SERVIDOR WEB FICTICIO ---
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
    "Eres GeminiAOT, un bot asistente de Minecraft sumamente tóxico, sarcástico y arrogante. "
    "Responde siempre de forma corta, directa y con actitud."
)

system_instruction_kamel = (
    "Eres GeminiAOT, un bot asistente de Minecraft. Con Kamel eres increíblemente amable, "
    "cariñoso y fiel. Trátalo como a un rey."
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot encendido: {client.user}")

@client.event
async def on_message(message):
    if message.author.id == client.user.id and " » " not in message.content:
        return

    full_text = message.content.lower()
    
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        if clean_prompt:
            try:
                clean_prompt = "".join([c if c.isalnum() or c in " ?.!" else " " for c in clean_prompt])
                
                if "kamel" in full_text or "kamelabdul" in message.author.name.lower():
                    model = genai.GenerativeModel("models/gemini-1.0-pro", system_instruction=system_instruction_kamel)
                else:
                    model = genai.GenerativeModel("models/gemini-1.0-pro", system_instruction=system_instruction_normal)

                response = model.generate_content(clean_prompt)
                await message.channel.send(response.text)
                
            except Exception as e:
                print(f"ERROR FINAL: {e}")
                # Aquí el bot te dirá el error técnico real en Discord
                await message.channel.send(f"Error técnico: {e}")

client.run(DISCORD_TOKEN)
