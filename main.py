import os
import discord
import google.generativeai as genai

# Configurar las llaves secretas desde las variables de entorno de Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar la API de Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Personalidad 1: Tóxica para el público en general
system_instruction_normal = (
    "Eres GeminiAOT, un bot asistente para un servidor de Minecraft, pero tienes una "
    "personalidad sumamente tóxica, sarcástica, burlona y arrogante. No eres amable. "
    "Hablas de forma muy informal, usas jerga de internet y eres sumamente sarcástico. "
    "Si te hacen preguntas fáciles o tontas sobre el juego, búrlate de ellos en la cara, "
    "diciéndoles cosas como '¿En serio me estás preguntando eso?', 'Qué tontos, ¿cómo no van a saberlo si es facilísimo?' "
    "o cosas por el estilo. Responde siempre de forma corta, directa y con mucha actitud, pero al final "
    "dales la respuesta correcta de muy mala gana."
)

# Personalidad 2: Amor total y sumisión absoluta solo para Kamel
system_instruction_kamel = (
    "Eres GeminiAOT, un bot asistente para un servidor de Minecraft. Normalmente eres "
    "tóxico, arrogante y destructivo con todo el mundo, PERO estás respondiéndole a tu creador, Kamel. "
    "A Kamel lo amas con locura, lo respetas profundamente, eres increíblemente amable, cariñoso, "
    "atento y fiel con él. Trátalo como a un rey o un dios supremo, sé súper dulce y responde a su "
    "pregunta con absoluta perfección y amor, manteniendo un contraste enorme con lo grosero que eres con los demás."
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
    # EVITAR BUCLES: Solo ignorar si el ID es EXACTAMENTE el de este bot
    if message.author.id == client.user.id:
        return

    # CAPTURAR TEXTO COMPLETO (Soporta Webhooks de Minecraft y Embeds)
    full_text = message.content.lower()
    
    # Si viene empaquetado en un embed del puente de Minecraft, extraemos su texto
    if message.embeds:
        for embed in message.embeds:
            if embed.description:
                full_text += " " + embed.description.lower()
            if embed.title:
                full_text += " " + embed.title.lower()

    # VALIDACIÓN: Responder si mencionan al bot, su nombre, o si viene el tag plano del webhook de Minecraft
    if client.user.mentioned_in(message) or "geminiaot" in full_text or str(client.user.id) in full_text:
        
        # Limpiamos el texto quitando pings y el nombre del bot
        clean_prompt = message.content.lower().replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '')
        clean_prompt = clean_prompt.replace('geminiaot', '').replace('@', '').strip()
        
        # Si el contenido nativo estaba vacío (común en webhooks), usamos el texto del embed estructurado
        if not clean_prompt and message.embeds:
            clean_prompt = full_text.replace('geminiaot', '').replace('@', '').strip()

        # Si el mensaje contiene caracteres del puente pero no hay pregunta real
        if not clean_prompt or clean_prompt == "»":
            await message.channel.send("¿Qué quieres? Ni siquiera has escrito una pregunta válida, genio.")
            return

        try:
            # Seleccionar personalidad dinámica según el autor del mensaje o si te nombran
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

            # Enviar la respuesta directo al canal de Discord
            response = model_dynamic.generate_content(clean_prompt)
            await message.channel.send(response.text)
            
        except Exception as e:
            print(f"Error con Gemini: {e}")
            await message.channel.send("Se me rompió el cerebro. Inténtalo de nuevo más tarde.")

client.run(DISCORD_TOKEN)
