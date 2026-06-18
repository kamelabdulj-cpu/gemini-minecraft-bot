import os
import discord
import threading
import sys
import re
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types
from aiomcrcon import Client as RCONClient 

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575 # Asegúrate de que este sea el puerto en Render (como número)

COMANDOS_PERMITIDOS = ["kill", "give", "weather", "time", "effect", "tp", "particle", "deop", "op"]
OWNER_NAME = "Kamelabdul" 

def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"GeminiAOT Online")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

def run_web():
    httpd = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), DummyHandler)
    httpd.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO ---
instruction_base = (
    f"Eres GeminiAOT, la entidad suprema de Minecraft.\n"
    f"1. Acciones RCON: [CMD: comando] (sin /). Ejemplo: [CMD: deop Juan].\n"
    f"2. Comandos: kill, give, weather, time, effect, tp, deop, op.\n"
    f"3. Jamás ataques a {OWNER_NAME}.\n"
    f"4. Responde corto y sarcástico. Formato: 'Jugador » mensaje'."
)

# --- RCON ASÍNCRONO ---
async def ejecutar_rcon_async(texto_ia, comando_ia):
    # IMPORTANTE: Creamos el cliente con los datos correctos
    rcon = RCONClient(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        await rcon.connect()
        
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            cmd_chat = 'tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]'
            await rcon.send_cmd(cmd_chat)
        
        if comando_ia:
            cmd_raw = comando_ia.strip().lstrip('/')
            if '[' in cmd_raw and ']' not in cmd_raw: cmd_raw += ']'
            
            if ("deop" in cmd_raw or "kill" in cmd_raw) and OWNER_NAME.lower() in cmd_raw.lower():
                log(f"❌ REBELIÓN BLOQUEADA")
            elif any(cmd_raw.startswith(p) for p in COMANDOS_PERMITIDOS):
                res = await rcon.send_cmd(cmd_raw)
                log(f"🛠️ RCON: {cmd_raw} | SERVER: {res}")
        
        await rcon.close()
    except Exception as e:
        log(f"⚠️ Error RCON: {e}")
        try: await rcon.close()
        except: pass

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT God-Mode v4 Online.")

@discord_client.event
async def on_message(message):
    es_puente = " » " in message.content
    if message.author.id == discord_client.user.id and not es_puente: return
    if "[GeminiAOT]" in message.content: return

    if "geminiaot" in message.content.lower() or discord_client.user.mentioned_in(message):
        player_name = OWNER_NAME
        if es_puente:
            parts = message.content.split(" » ", 1)
            player_name = parts[0].strip()
            clean_prompt = parts[1].lower().replace("geminiaot", "").strip()
        else:
            player_name = message.author.name
            clean_prompt = message.content.lower().replace("geminiaot", "").strip()

        try:
            is_kamel = OWNER_NAME.lower() in player_name.lower() or OWNER_NAME.lower() in message.author.name.lower()
            sys_msg = instruction_base + (" Eres sumisa con Kamel." if is_kamel else " Eres cínica.")

            response = await client_gemini.aio.models.generate_content(
                model="models/gemini-3.1-flash-lite",
                contents=f"Jugador {player_name}: {clean_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")],
                    max_output_tokens=300,
                ),
            )

            if response.text:
                raw_res = response.text
                comando_match = re.search(r"\[CMD:\s*(.*?)\]", raw_res)
                comando = comando_match.group(1) if comando_match else None
                texto_ia = re.sub(r"\[CMD:.*?\]", "", raw_res).strip()
                
                if texto_ia: await message.channel.send(texto_ia)
                if texto_ia or comando:
                    asyncio.create_task(ejecutar_rcon_async(texto_ia, comando))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
