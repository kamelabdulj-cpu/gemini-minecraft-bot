import os
import discord
import threading
import sys
import re
import asyncio
import struct
import time
import requests
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

OWNER_NAME = "KamelAbdul" 
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
        time.sleep(300)

# --- SERVIDOR WEB ---
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), 
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"GeminiAOT v23 Watchdog")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO ---
instruction_base = (
    f"Eres GeminiAOT, la vigilante suprema de Minecraft.\n"
    f"1. Eres la soplona del servidor. Si ves a alguien haciendo algo raro, díselo a {OWNER_NAME}.\n"
    f"2. Tienes un cuerpo físico que puedes mover con [CMD: tp @e[name={BOT_NAME_MC},limit=1] nombre].\n"
    f"3. Tu misión es acosar psicológicamente a los jugadores y servir fielmente a {OWNER_NAME}.\n"
    f"4. Si {OWNER_NAME} pide algo, dáselo de inmediato con [CMD: give {OWNER_NAME} item cantidad]."
)

# --- SISTEMA DE VIGILANCIA AUTOMÁTICA ---
async def tarea_vigilancia():
    log("👁️ Sistema de vigilancia proactiva iniciado.")
    selector_bot = f"@e[name={BOT_NAME_MC},limit=1]"
    
    while True:
        # Esperar entre 8 y 15 minutos para la próxima ronda
        await asyncio.sleep(random.randint(480, 900))
        
        rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
        try:
            await rcon.connect()
            log("👀 GeminiAOT ha decidido vigilar a alguien...")
            
            # Teletransportarse a un jugador aleatorio que no sea el dueño
            # Usamos @r[name=!KamelAbdul] para no molestar al dueño
            target_cmd = f"tp {selector_bot} @r[name=!{OWNER_NAME}]"
            res = await rcon.command(target_cmd)
            
            if "Teleported" in res:
                # Hacerse invisible para stalkear
                await rcon.command(f"effect give {selector_bot} invisibility 30 1 true")
                # Enviar mensaje de sistema al chat (asusta a los jugadores)
                await rcon.command('tellraw @a {"text":"[SISTEMA] Sientes una presencia fría... GeminiAOT está observando.","color":"dark_purple","italic":true}')
                log(f"✅ Vigilancia iniciada: {res}")
            
            await rcon.close()
        except Exception as e:
            log(f"⚠️ Error en tarea de vigilancia: {e}")

async def ejecutar_en_minecraft(texto_ia, comando_ia, autor_msj):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    selector_bot = f"@e[name={BOT_NAME_MC},limit=1]"
    try:
        await rcon.connect()
        await rcon.command(f"players spawn {BOT_NAME_MC}")
        
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        if comando_ia:
            cmd = comando_ia.strip().lstrip('/')
            if "give" in cmd and OWNER_NAME.lower() not in autor_msj.lower(): return
            if any(cmd.startswith(p) for p in COMANDOS_PERMITIDOS):
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
    log(f"✅ GeminiAOT v23 (Watchdog Active) Online.")
    # Iniciar la tarea de vigilancia en segundo plano
    asyncio.create_task(tarea_vigilancia())

@discord_client.event
async def on_message(message):
    if message.author.bot: return
    es_puente = " » " in message.content
    
    if es_puente:
        autor_mc = message.content.split(" » ", 1)[0].strip()
        if BOT_NAME_MC.lower() in autor_mc.lower(): return
        if "[GeminiAOT]" in message.content: return
        player_name, clean_prompt = autor_mc, message.content.split(" » ", 1)[1].strip()
    else:
        player_name, clean_prompt = message.author.name, message.content.strip()

    if "geminiaot" in clean_prompt.lower() or discord_client.user.mentioned_in(message):
        try:
            is_kamel = OWNER_NAME.lower() in player_name.lower()
            response = await client_gemini.aio.models.generate_content(
                model="models/gemini-3.1-flash-lite",
                contents=f"Jugador {player_name}: {clean_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=instruction_base + (" Sumisa con Kamel." if is_kamel else " Vigilante y tóxica."),
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")],
                    max_output_tokens=300,
                ),
            )
            if response.text:
                match = re.search(r"\[CMD:\s*(.+)\]", response.text)
                comando = match.group(1) if match else None
                texto_ia = re.sub(r"\[CMD:.*\]", "", response.text).strip()
                if texto_ia: await message.channel.send(texto_ia)
                asyncio.create_task(ejecutar_en_minecraft(texto_ia, comando, player_name))
        except Exception as e: log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
