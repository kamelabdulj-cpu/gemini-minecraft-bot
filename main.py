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

# --- CONFIGURACIÓN ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RCON_IP = "34.186.32.18"
RCON_PASS = "16827131"
RCON_PORT = 25575

OWNER_NAME = "KamelAbdul" # Exacto como en Minecraft
BOT_NAME_MC = "GeminiAOT" # Tu nombre en el juego

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
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"GeminiAOT v16 Fixed")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO ---
instruction_base = (
    f"Eres GeminiAOT, entidad física de Minecraft.\n"
    f"SINTAXIS CORRECTA RCON:\n"
    f"- Aparecer: [CMD: players spawn GeminiAOT]\n"
    f"- Mover brazo: [CMD: players action GeminiAOT attack]\n"
    f"- Mirar a dueño: [CMD: players action GeminiAOT look {OWNER_NAME}]\n"
    f"REGLAS: Eres arrogante con todos y sumisa con {OWNER_NAME}.\n"
    f"Formato: 'Jugador » mensaje'. Responde corto."
)

async def ejecutar_en_minecraft(texto_ia, comando_ia, autor_msj):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        await rcon.connect()
        # 1. Asegurar presencia (Sintaxis que funcionó en tus logs)
        await rcon.command(f"players spawn {BOT_NAME_MC}")
        
        # 2. Chat
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        # 3. Comandos
        if comando_ia:
            cmd = comando_ia.strip().lstrip('/')
            # Corrección de orden si la IA se equivoca
            if f"{BOT_NAME_MC} spawn" in cmd: cmd = f"players spawn {BOT_NAME_MC}"
            
            es_dueno = OWNER_NAME.lower() in autor_msj.lower()
            if cmd.startswith("give") and not es_dueno: return
            if ("kill" in cmd or "deop" in cmd) and OWNER_NAME.lower() in cmd.lower(): return

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
    log(f"✅ GeminiAOT v16 (Anti-Spam) Online.")

@discord_client.event
async def on_message(message):
    # --- FILTRO ANTI-SPAM DEFINITIVO ---
    es_puente = " » " in message.content
    
    # 1. Si el mensaje NO es del puente y es del bot, ignorar
    if message.author.id == discord_client.user.id and not es_puente:
        return

    # 2. Si el mensaje ES del puente, verificar quién es el jugador original
    if es_puente:
        player_name_mc = message.content.split(" » ", 1)[0].strip()
        # SI EL JUGADOR ES EL MISMO BOT, IGNORAR (Evita el bucle)
        if player_name_mc == BOT_NAME_MC:
            return

    # 3. Solo procesar si mencionan al bot
    if "geminiaot" in message.content.lower() or discord_client.user.mentioned_in(message):
        
        # Extraer nombre real para la IA
        if es_puente:
            parts = message.content.split(" » ", 1)
            player_name = parts[0].strip()
            clean_prompt = parts[1].strip()
        else:
            player_name = message.author.name
            clean_prompt = message.content.strip()

        try:
            is_kamel = OWNER_NAME.lower() in player_name.lower()
            sys_msg = instruction_base + (" Sumisa con Kamel." if is_kamel else " Arrogante.")

            # Llamada a la IA
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
                
                # Enviar a Discord
                if texto_ia: await message.channel.send(texto_ia)
                # Ejecutar RCON
                asyncio.create_task(ejecutar_en_minecraft(texto_ia, comando, player_name))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
