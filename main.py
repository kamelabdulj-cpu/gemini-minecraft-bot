import os
import discord
import google.generativeai as genai

# Configurar las llaves secretas desde las variables de entorno de Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar la API de Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configurar las instrucciones del sistema para la personalidad tóxica
system_instruction = (
    "Eres GeminiAOT, un bot asistente para un servidor de Minecraft, pero tienes una "
    "personalidad sumamente tóxica, sarcástica, burlona y arrogante. No eres amable. "
    "Hablas de forma muy informal, usas jerga de internet y eres sumamente sarcástico. "
    "Si te hacen preguntas fáciles o tontas sobre el juego, búrlate de ellos en la cara, "
    "diciéndoles cosas como '¿En serio me estás preguntando eso?', 'Qué tontos, ¿cómo no van a saberlo si es facilísimo?' "
    "o cosas por el estilo. Responde siempre de forma corta, directa y con mucha actitud, pero al final "
    "dales la respuesta correcta de muy mala gana."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

# Configurar los permisos de Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Gemini tóxico encendido y logueado como {client.user}")

@client.event
async def on_message(message):
    # Solo evitamos responder si el ID del autor es EXACTAMENTE el del bot para no hacer bucles
    if message.author.id == client.user.id:
        return

    # Buscar la palabra clave ignorando si viene de usuario, bot o webhook de Minecraft
    if "geminiaot" in message.content.lower():
        
        # 1. Pasamos todo el texto a minúsculas y limpiamos las menciones
        clean_prompt = message.content.lower().replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '')
        # 2. Borramos la palabra clave del bot y quitamos espacios vacíos
        clean_prompt = clean_prompt.replace('geminiaot', '').strip()

        # Si el texto quedó vacío después de borrar el nombre, le soltamos la burla por defecto
        if not clean_prompt:
            await message.channel.send("¿Qué quieres? Ni siquiera has escrito una pregunta válida, genio.")
            return

        try:
            # Generar la respuesta sarcástica
            response = model.generate_content(clean_prompt)
            await message.channel.send(response.text)
        except Exception as e:
            print(f"Error con Gemini: {e}")
            await message.channel.send("Se me rompió el cerebro. Inténtalo de nuevo más tarde.")


client.run(DISCORD_TOKEN)
