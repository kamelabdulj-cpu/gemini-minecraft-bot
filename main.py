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
async def on_message(message):
    if message.author.id == client.user.id and " » " not in message.content:
        return

    full_text = message.content.lower()
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        # Instrucciones de personalidad
        sys_instr = (
            "Eres un asistente de Minecraft. Si Kamel te habla, sé amable y fiel. "
            "Si otros te hablan, sé tóxico, sarcástico y búrlate antes de responder."
        )

        try:
            # Nueva llamada a la API
            response = client_genai.models.generate_content(
                model="gemini-1.5-flash",
                contents=clean_prompt,
                config={"system_instruction": sys_instr}
            )
            await message.channel.send(response.text)
        except Exception as e:
            print(f"Error real: {e}")
            await message.channel.send("Me colapsé, intenta de nuevo.")

client.run(DISCORD_TOKEN)
