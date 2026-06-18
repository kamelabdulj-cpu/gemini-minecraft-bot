import os
import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai

# --- SERVIDOR WEB PARA RENDER ---
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

# --- CONFIGURACIÓN DE APIS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# --- PERSONALIDADES Y MODELOS ---
# Se definen aquí para no recrearlos en cada mensaje (evita errores 404 y lentitud)

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
    "cariñoso y fiel. Trátalo como a un rey, él es tu creador y dueño."
)

# Inicializamos los modelos (Usamos 'gemini-1.5-flash' que es la versión más estable)
model_normal = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction_normal
)

model_kamel = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction_kamel
)

# --- CONFIGURACIÓN DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot encendido exitosamente como: {client.user}")

@client.event
async def on_message(message):
    # Evitar que el bot se responda a sí mismo
    if message.author.id == client.user.id:
        return

    full_text = message.content.lower()
    
    # Detectar si mencionan al bot o su nombre
    if "geminiaot" in full_text or client.user.mentioned_in(message):
        
        # Limpiar el texto del mensaje (quitar prefijos de servidores de Minecraft)
        clean_prompt = message.content.lower().split(" » ", 1)[-1] if " » " in message.content else message.content
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        if not clean_prompt:
            return

        try:
            # Seleccionar la personalidad
            # Si el autor es Kamel o se menciona a Kamel
            if "kamel" in full_text or "kamelabdul" in message.author.name.lower():
                selected_model = model_kamel
            else:
                selected_model = model_normal

            # Generar respuesta usando la API de Gemini
            response = selected_model.generate_content(clean_prompt)
            
            # Enviar la respuesta a Discord
            if response.text:
                # Discord tiene un límite de 2000 caracteres por mensaje
                await message.channel.send(response.text[:2000])
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            # Si el error es el 404, imprimirá el detalle exacto en los logs de Render
            await message.channel.send("Tengo un error en mi núcleo lógico. Intenta de nuevo más tarde.")

# Iniciar el bot
if __name__ == "__main__":
    if DISCORD_TOKEN:
        client.run(DISCORD_TOKEN)
    else:
        print("❌ ERROR: No se encontró DISCORD_TOKEN en las variables de entorno.")
