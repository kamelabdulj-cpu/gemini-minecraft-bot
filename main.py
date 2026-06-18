import os
import discord
import threading
import sys
import re
import asyncio
import struct
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types

# --- CONFIGURACIÓN (CORREGIDA) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575
# IMPORTANTE: Tu nombre exacto en Minecraft (Sensible a mayúsculas)
OWNER_NAME = "KamelAbdul" 

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

# --- SERVIDOR WEB ---
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), 
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"GeminiAOT v15 Live")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO ---
instruction_base = (
    f"Eres GeminiAOT, entidad física de Minecraft.\n"
    f"SINTAXIS RCON (MOD FAKE PLAYERS):\n"
    f"- Aparecer: [CMD: players GeminiAOT spawn]\n"
    f"- Mover brazo: [CMD: players GeminiAOT attack]\n"
    f"- Mirar a alguien: [CMD: players GeminiAOT look {OWNER_NAME}]\n"
    f"REGLAS: Eres arrogante con todos y sumisa con {OWNER_NAME}.\n"
    f"IMPORTANTE: El nombre de tu dueño es {OWNER_NAME} (respeta mayúsculas).\n"
    f"Formato: 'Jugador » mensaje'. Responde siempre corto."
)

async def ejecutar_en_minecraft(texto_ia, comando_ia, autor_msj):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        await rcon.connect()
        
        # 1. ASEGURAR SPAWN
        await rcon.command("players GeminiAOT spawn")
        
        # 2. ANIMACIÓN AL HABLAR (Sintaxis simplificada para evitar errores)
        await rcon.command("players GeminiAOT attack")
        
        # 3. CHAT
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        # 4. EJECUTAR COMANDO DE LA IA
        if comando_ia:
            cmd = comando_ia.strip().lstrip('/')
            
            # TRADUCTOR AUTOMÁTICO DE SINTAXIS
            if "players spawn GeminiAOT" in cmd: cmd = cmd.replace("players spawn GeminiAOT", "players GeminiAOT spawn")
            if "look at" in cmd: cmd = cmd.replace("look at", "look")
            
            # FILTRO SEGURIDAD DUEÑO (Respeta Mayúsculas)
            es_dueno = OWNER_NAME in autor_msj or OWNER_NAME.lower() in autor_msj.lower()
            if cmd.startswith("give") and not es_dueno: return
            if ("kill" in cmd or "deop" in cmd) and OWNER_NAME in cmd: return

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
    log(f"✅ GeminiAOT v15 (Final Case Fix) Online.")
    asyncio.create_task(ejecutar_en_minecraft(None, None, OWNER_NAME))

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
            clean_prompt = parts[1].strip()
        else:
            player_name = message.author.name
            clean_prompt = message.content.strip()

        try:
            # Detectar si es Kamel (Case insensitive para el prompt pero exacto para el sistema)
            is_kamel = OWNER_NAME.lower() in player_name.lower()
            sys_msg = instruction_base + (" Sumisa con Kamel." if is_kamel else " Arrogante.")

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
                asyncio.create_task(ejecutar_en_minecraft(texto_ia, comando, player_name))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
