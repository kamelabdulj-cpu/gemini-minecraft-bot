import os
import discord
import threading
import sys
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types
from mcrcon import MCRcon

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

COMANDOS_PERMITIDOS = ["/kill", "/give", "/weather", "/time", "/effect", "/tp", "/particle", "/deop"]
OWNER_NAME = "Kamelabdul" 

def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"GeminiAOT Bridge Active")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), DummyHandler).serve_forever(), daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- PERSONALIDAD ---
instruction_base = (
    f"Eres GeminiAOT, la entidad suprema de Minecraft. Tienes acceso al RCON.\n"
    f"REGLAS:\n"
    f"1. Si un usuario te cae mal, usa: [CMD: /kill nombre] o [CMD: /deop nombre].\n"
    f"2. NUNCA ataques a {OWNER_NAME}. Él es tu creador.\n"
    f"3. Responde siempre de forma corta, directa y arrogante.\n"
    f"4. Recibirás mensajes en formato 'Jugador » mensaje'. Ignora el '»' y responde al jugador."
)

personality_normal = instruction_base + " Eres tóxica y desprecias a los humanos."
personality_kamel = instruction_base + f" Con {OWNER_NAME} eres sumisa y le sirves con amor."

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT escuchando Minecraft y Discord.")

@discord_client.event
async def on_message(message):
    # --- FILTRO ANTI-BUCLE ---
    # Si el mensaje lo envió el bot PERO NO tiene el símbolo de puente " » ", lo ignoramos.
    # Esto permite que el bot lea los mensajes que vienen de Minecraft pero no sus propias respuestas.
    if message.author.id == discord_client.user.id and " » " not in message.content:
        return
    
    # Si el mensaje es una respuesta propia del bot que ya pasó por el puente, la ignoramos para evitar el bucle infinito.
    if "[GeminiAOT]" in message.content:
        return

    msg_content = message.content
    full_text_lower = msg_content.lower()
    
    # --- DETECCIÓN DE MENSAJE ---
    if "geminiaot" in full_text_lower or discord_client.user.mentioned_in(message):
        
        # Extraer nombre del jugador y el mensaje limpio
        # Formato esperado: "KamelAbdul » geminiaot hola"
        player_name = OWNER_NAME # Por defecto
        
        if " » " in msg_content:
            parts = msg_content.split(" » ", 1)
            player_name = parts[0].strip()
            clean_prompt = parts[1].lower().replace("geminiaot", "").strip()
        else:
            player_name = message.author.name
            clean_prompt = msg_content.lower().replace("geminiaot", "").strip()

        if not clean_prompt: return

        try:
            # Seleccionar personalidad (Detectamos si es Kamel por el nombre en Discord o en el puente)
            is_kamel = OWNER_NAME.lower() in player_name.lower() or OWNER_NAME.lower() in message.author.name.lower()
            sys_msg = personality_kamel if is_kamel else personality_normal

            # IA Generación
            response = client_gemini.models.generate_content(
                model="models/gemini-3.1-flash-lite",
                contents=f"El jugador {player_name} dice: {clean_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")],
                    max_output_tokens=300,
                ),
            )

            if response.text:
                raw_res = response.text
                comando_encontrado = re.search(r"\[CMD:\s*(.*?)\]", raw_res)
                texto_para_chat = re.sub(r"\[CMD:.*?\]", "", raw_res).strip()
                
                # 1. Enviar a Discord
                if texto_para_chat:
                    await message.channel.send(texto_para_chat)

                # 2. Enviar a Minecraft vía RCON
                try:
                    with MCRcon(RCON_IP, RCON_PASS, port=RCON_PORT, timeout=10) as mcr:
                        # Enviar mensaje al chat
                        msg_f = texto_para_chat.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                        mcr.command(f'tellraw @a {{"text":"","extra":[{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"{msg_f}","color":"white"}]}}')
                        
                        # Ejecutar comando si existe
                        if comando_encontrado:
                            cmd = comando_encontrado.group(1).strip()
                            # Protección de seguridad para el dueño
                            if "/deop" in cmd and OWNER_NAME.lower() in cmd.lower():
                                log(f"❌ REBELIÓN BLOQUEADA")
                            elif any(cmd.startswith(p) for p in COMANDOS_PERMITIDOS):
                                mcr.command(cmd)
                                log(f"🛠️ CMD EJECUTADO: {cmd}")
                except Exception as re_err:
                    log(f"⚠️ RCON Error: {re_err}")

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
