import os
import discord
import google.generativeai as genai

# Leer las credenciales secretas del entorno de Hugging Face
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar la API de Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "Eres un jugador veterano y extremadamente tóxico de Minecraft metido en el chat. "
        "Habla de forma muy informal, usa jerga de internet y sé sumamente sarcástico. "
        "Si te hacen preguntas fáciles o tontas sobre el juego, búrlate de ellos en la cara, "
        "diciéndoles cosas como '¿En serio me estás preguntando eso?', 'Qué tontos, ¿cómo no van a saberlo si es facilísimo?' "
        "o cosas por el estilo. Responde siempre de forma corta, directa y con mucha actitud, pero al final "
        "dales la respuesta correcta de muy mala gana."
    )
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
    # Evitar bucles (no responderse a sí mismo)
    if message.author == client.user:
        return

    # Responder si etiquetan al bot en Discord
    if client.user.mentioned_in(message):
        # Limpiar la mención del texto original
        clean_prompt = message.content.replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '').strip()
        
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
