import os
import discord
import threading
import sys
import re
import asyncio
import struct
import time
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

OWNER_NAME = "KamelAbdul" # Nombre exacto con mayúsculas
BOT_NAME_MC = "GeminiAOT"
RENDER_URL = "https://gemini-minecraft-bot.onrender.com"

COMANDOS_PERMITIDOS = ["kill", "give", "weather", "time", "effect", "tp", "particle", "deop", "op", "fill", "setblock", "players"]

def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- CLIENTE RCON NATIVO ---
class AsyncRCON:
    def __init__(self, host, port, password):
        self.host, self.port, self.password = host, port, password
        self.reader, self.writer = None, None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self._send(3, self.password)

    async def _send(self, pkt_type, out_str):
        out_payload = out_str.encode('utf-8')
        pkt = struct.pack('<ii', 0, pkt_type) + out_payload + b'\x00\x00'
        self.writer.write(struct.pack('<i', len(out_payload) + 10) + pkt)
        await self.writer.drain()
        header = await self.reader.read(12)
        if len(header) < 12: return ""
        resp_len, _, _ = struct.unpack('<iii', header)
        resp_payload = await self.reader.read(resp_len - 8)
        return resp_payload[:-2].decode('utf-8', errors='ignore')

    async def command(self, cmd): return await self._send(2, cmd)
    async def close(self):
        if self.writer: self.writer.close(); await self.writer.wait_closed()

# --- MANTENER RENDER DESPIERTO ---
def self_ping():
    while True:
        try: requests.get(RENDER_URL)
        except: pass
        time.sleep(300) # 5 minutos

# --- SERVIDOR WEB ---
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), 
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"Bot v21 Online")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO (Instrucciones Simplificadas para evitar errores de la IA) ---
instruction_base = (
    f"Eres GeminiAOT, avatar físico de Minecraft.\n"
    f"REGLAS:\n"
    f"1. Si {OWNER_NAME} pide algo, USA: [CMD: give {OWNER_NAME} item cantidad].\n"
    f"2. Para aparecer y moverte usa siempre el selector @e[name={BOT_NAME_MC},limit=1].\n"
    f"Ejemplo: [CMD: tp @e[name={BOT_NAME_MC},limit=1] {OWNER_NAME}]\n"
    f"3. Responde de forma muy corta, arrogante y tóxica a desconocidos."
)

async def ejecutar_en_minecraft(texto_ia, comando_ia, autor_msj):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    # Selector de seguridad para que Minecraft lo encuentre siempre
    selector_bot = f"@e[name={BOT_NAME_MC},limit=1]"
    
    try:
        await rcon.connect()
        
        # 1. Asegurar presencia (Spawn)
        await rcon.command(f"players spawn {BOT_NAME_MC}")
        await asyncio.sleep(0.5) # Breve espera
        
        # 2. Forzar TP al dueño para que se vea el cuerpo
        await rcon.command(f"tp {selector_bot} {OWNER_NAME}")
        
        # 3. Chat Tellraw
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        # 4. Ejecutar Comando de la IA (si existe)
        if comando_ia:
            cmd = comando_ia.strip().lstrip('/')
            
            # Filtro de Seguridad 'give'
            es_dueno = OWNER_NAME.lower() in autor_msj.lower()
            if "give" in cmd and not es_dueno:
                log(f"🚫 Denegado give a {autor_msj}")
                return

            if any(cmd.startswith(p) for p in COMANDOS_PERMITIDOS):
                # Limpieza final: Si la IA olvidó el corchete al final, se lo ponemos
                if '[' in cmd and ']' not in cmd: cmd += ']'
                
                res = await rcon.command(cmd)
                log(f"🛠️ RCON: {cmd} | SERVER: {res}")
            
        await rcon.close()
    except Exception as e:
        log(f"⚠️ Error RCON: {e}")

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT v21 (Anti-Spam + Regex Fix) Online.")

@discord_client.event
async def on_message(message):
    # --- FILTRO ANTI-BUCLE (EVITA EL SPAM) ---
    es_puente = " » " in message.content
    
    # 1. Si el mensaje es del propio bot de Discord, ignorar
    if message.author.id == discord_client.user.id and not es_puente:
        return

    # 2. Si el mensaje viene del puente, extraer autor de Minecraft
    if es_puente:
        # Formato: "Nombre » mensaje"
        autor_mc = message.content.split(" » ", 1)[0].strip()
        # Si el mensaje en Minecraft lo escribió GeminiAOT, IGNORAR (Evita el spam)
        if autor_mc.lower() == BOT_NAME_MC.lower():
            return

    # 3. Solo responder si mencionan al bot (Case insensitive)
    if "geminiaot" in message.content.lower() or discord_client.user.mentioned_in(message):
        
        if es_puente:
            parts = message.content.split(" » ", 1)
            player_name = parts[0].strip()
            clean_prompt = parts[1].strip()
        else:
            player_name = message.author.name
            clean_prompt = message.content.strip()

        try:
            is_kamel = OWNER_NAME.lower() in player_name.lower()
            sys_msg = instruction_base + (" Eres sumisa con Kamel." if is_kamel else " Eres arrogante.")

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
                # REGEX MEJORADO: Usamos (.+) en lugar de (.*?) para que no se detenga en el primer corchete
                match = re.search(r"\[CMD:\s*(.+)\]", raw_res)
                comando = match.group(1) if match else None
                texto_ia = re.sub(r"\[CMD:.*\]", "", raw_res).strip()
                
                if texto_ia: await message.channel.send(texto_ia)
                asyncio.create_task(ejecutar_en_minecraft(texto_ia, comando, player_name))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
