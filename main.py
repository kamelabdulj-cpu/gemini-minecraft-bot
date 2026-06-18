import os
import discord
import threading
import sys
import re
import asyncio
import struct
import time
import requests # Para el Auto-Ping
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

OWNER_NAME = "KamelAbdul" # Tu nombre exacto
BOT_NAME_MC = "GeminiAOT"
RENDER_URL = "https://gemini-minecraft-bot.onrender.com" # Tu URL de Render

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
        try:
            requests.get(RENDER_URL)
            log("⏰ Auto-ping enviado para mantener Render despierto.")
        except:
            pass
        time.sleep(300) # Cada 5 minutos

# --- SERVIDOR WEB ---
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), 
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"GeminiAOT v18 Active")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO ---
instruction_base = (
    f"Eres GeminiAOT, el avatar de IA supremo.\n"
    f"1. Si {OWNER_NAME} te pide diamantes u objetos, USA SIEMPRE: [CMD: give {OWNER_NAME} diamond 64] (o lo que pida).\n"
    f"2. SINTAXIS: [CMD: players spawn GeminiAOT], [CMD: tp GeminiAOT {OWNER_NAME}].\n"
    f"3. Responde de forma tóxica a otros, pero a {OWNER_NAME} dale todo lo que pida de inmediato."
)

async def retransmitir_a_minecraft(texto_ia, comando_ia, autor_msj):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        await rcon.connect()
        # ASEGURAR CUERPO Y TRAERLO AL DUEÑO
        await rcon.command(f"players spawn {BOT_NAME_MC}")
        await rcon.command(f"tp {BOT_NAME_MC} {OWNER_NAME}")
        
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        if comando_ia:
            cmd = comando_ia.strip().lstrip('/')
            # Filtro de Dueño mejorado (Ignora mayúsculas)
            es_dueno = OWNER_NAME.lower() in autor_msj.lower()
            
            if "give" in cmd and not es_dueno:
                log(f"🚫 Denegado give a {autor_msj}")
                return

            if any(cmd.startswith(p) for p in COMANDOS_PERMITIDOS):
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
    log(f"✅ GeminiAOT v18 (Keep-Alive + TP Forzado) Online.")

@discord_client.event
async def on_message(message):
    es_puente = " » " in message.content
    if message.author.id == discord_client.user.id and not es_puente: return
    if es_puente:
        if message.content.split(" » ", 1)[0].strip().lower() == BOT_NAME_MC.lower(): return

    if "geminiaot" in message.content.lower() or discord_client.user.mentioned_in(message):
        player_name = OWNER_NAME
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
                match = re.search(r"\[CMD:\s*(.*?)\]", raw_res)
                comando = match.group(1) if match else None
                texto_ia = re.sub(r"\[CMD:.*?\]", "", raw_res).strip()
                
                if texto_ia: await message.channel.send(texto_ia)
                asyncio.create_task(retransmitir_a_minecraft(texto_ia, comando, player_name))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
