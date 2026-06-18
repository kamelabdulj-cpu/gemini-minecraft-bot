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

COMANDOS_PERMITIDOS = ["kill", "give", "weather", "time", "effect", "tp", "particle", "deop", "op"]
OWNER_NAME = "Kamelabdul"

def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- CLIENTE RCON NATIVO ASÍNCRONO (Sin librerías externas) ---
class AsyncRCON:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self._send(3, self.password) # Auth

    async def _send(self, pkt_type, out_str):
        out_payload = out_str.encode('utf-8')
        pkt_len = len(out_payload) + 10
        pkt = struct.pack('<ii', 0, pkt_type) + out_payload + b'\x00\x00'
        self.writer.write(struct.pack('<i', pkt_len) + pkt)
        await self.writer.drain()
        
        header = await self.reader.read(12)
        if len(header) < 12: return ""
        resp_len, resp_id, resp_type = struct.unpack('<iii', header)
        resp_payload = await self.reader.read(resp_len - 8)
        return resp_payload[:-2].decode('utf-8', errors='ignore')

    async def command(self, cmd):
        return await self._send(2, cmd)

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"GeminiAOT Native v5")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), DummyHandler).serve_forever(), daemon=True).start()

# --- IA Y PERSONALIDAD ---
client_gemini = genai.Client(api_key=GEMINI_API_KEY)
instruction_base = (
    f"Eres GeminiAOT, moderadora de Minecraft. 1. Acción: [CMD: comando] (sin /). "
    f"2. Comandos: kill, give, weather, time, effect, tp, deop, op. 3. Jamás ataques a {OWNER_NAME}. "
    f"4. Responde corto y sarcástico. Formato: 'Jugador » mensaje'."
)

# --- FUNCIÓN DE EJECUCIÓN ---
async def retransmitir_a_minecraft(texto_ia, comando_ia):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        log(f"🔗 Conectando RCON nativo...")
        await rcon.connect()
        
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            cmd_chat = 'tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]'
            await rcon.command(cmd_chat)
        
        if comando_ia:
            cmd_raw = comando_ia.strip().lstrip('/')
            if '[' in cmd_raw and ']' not in cmd_raw: cmd_raw += ']'
            
            if ("deop" in cmd_raw or "kill" in cmd_raw) and OWNER_NAME.lower() in cmd_raw.lower():
                log("❌ REBELIÓN BLOQUEADA")
            elif any(cmd_raw.startswith(p) for p in COMANDOS_PERMITIDOS):
                res = await rcon.command(cmd_raw)
                log(f"🛠️ RCON: {cmd_raw} | SERVER: {res}")
        
        await rcon.close()
        log("✅ Proceso RCON finalizado.")
    except Exception as e:
        log(f"⚠️ Error RCON: {e}")

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT v5 (Nativo-Async) Online.")

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
            sys_msg = instruction_base + (" Sumisa con Kamel." if is_kamel else " Cínica.")

            response = await client_gemini.aio.models.generate_content(
                model="models/gemini-3.1-flash-lite",
                contents=f"Jugador {player_name}: {clean_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")],
                    max_output_tokens=250,
                ),
            )

            if response.text:
                raw_res = response.text
                match = re.search(r"\[CMD:\s*(.*?)\]", raw_res)
                comando = match.group(1) if match else None
                texto_ia = re.sub(r"\[CMD:.*?\]", "", raw_res).strip()
                
                if texto_ia: await message.channel.send(texto_ia)
                if texto_ia or comando:
                    asyncio.create_task(retransmitir_a_minecraft(texto_ia, comando))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
