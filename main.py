import os
import discord
import google.generativeai as genai
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- SERVIDOR WEB FALSO PARA ENGAÑAR A RENDER Y QUE NO SE APAGUE ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot encendido y escuchando perfectamente!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# Iniciamos el servidor en segundo plano
threading.Thread(target=run_dummy_server, daemon=True).start()
# -------------------------------------------------------------------

# Configurar las llaves secretas
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Personalidades
system_instruction_normal = (
    "Eres GeminiAOT, un bot asistente para un servidor de Minecraft, pero tienes una "
    "personalidad sumamente tóxica, sarcástica, burlona y arrogante. No eres amable. "
    "Hablas de forma muy informal, usas jerga de internet y eres sumamente sarcástico. "
    "Si te hacen preguntas fáciles o tontas sobre el juego, búrlate de ellos en la cara. "
    "Responde siempre de forma corta, directa y con mucha actitud, pero al final "
    "dales la respuesta correcta de muy mala gana."
)

system_instruction_kamel = (
    "Eres GeminiAOT, un bot asistente para un servidor de Minecraft. Normalmente eres "
    "tóxico, arrogante y destructivo con todo el mundo, PERO estás respondiéndole a tu creador, Kamel. "
    "A Kamel lo amas con locura, lo respetas profundamente, eres increíblemente amable, cariñoso, "
    "atento y fiel con él. Trátalo como a un rey, sé súper dulce y responde a su "
    "pregunta con absoluta perfección y amor."
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Gemini tóxico encendido y logueado como {client.user}")

@client.event
async def on_message(message):
    # LA SOLUCIÓN DEL PUENTE: Si el mensaje lo envía el mismo bot (GeminiAOT)...
    if message.author.id == client.user.id:
        # Revisamos si tiene el símbolo " » " de Minecraft.
        # Si NO lo tiene, significa que es una respuesta de la IA, la ignoramos para evitar bucles.
        if " » " not in message.content:
            return

    full_text = message.content.lower()
    
    if message.embeds:
        for embed in message.embeds:
            if embed.description: full_text += " " + embed.description.lower()
            if embed.title: full_text += " " + embed.title.lower()

    if client.user.mentioned_in(message) or "geminiaot" in full_text or str(client.user.id) in full_text:
        
        # Extraemos solo la pregunta (borramos el "benja_37 »" para no confundir a la IA)
        clean_prompt = message.content.lower()
        if " » " in clean_prompt:
            clean_prompt = clean_prompt.split(" » ", 1)[1]
            
        # Limpiamos las menciones y el nombre del bot
        clean_prompt = clean_prompt.replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '')
        clean_prompt = clean_prompt.replace('geminiaot', '').replace('@', '').strip()

        if not clean_prompt and message.embeds:
            clean_prompt = full_text.replace('geminiaot', '').replace('@', '').strip()

        if not clean_prompt:
            await message.channel.send("¿Qué quieres? Ni siquiera has escrito una pregunta válida, genio.")
            return

        try:
            # Si lee que eres Kamel (ya sea desde Discord o el nombre del chat de Minecraft)
            if "kamel" in full_text or "kamelabdul" in message.author.name.lower():
                model_dynamic = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction_kamel
                )
            else:
                model_dynamic = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction_normal
                )

            response = model_dynamic.generate_content(clean_prompt)
            await message.channel.send(response.text)
            
        except Exception as e:
            print(f"Error con Gemini: {e}")
            await message.channel.send("Se me rompió el cerebro. Inténtalo de nuevo más tarde.")

client.run(DISCORD_TOKEN)
