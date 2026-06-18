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

# Comandos permitidos
COMANDOS_PERMITIDOS = ["kill", "give", "weather", "time", "effect", "tp", "particle", "deop", "op"]
OWNER_NAME = "Kamelabdul"

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
    type('D', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"GeminiAOT Protected")),
                                          'do_HEAD': lambda s: (s.send_response(200), s.end_headers())})).serve_forever(), daemon=True).start()

# --- IA Y PERSONALIDAD ---
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# INSTRUCCIONES ESTRICTAS: Solo Kamel manda.
instruction_base = (
    f"Eres GeminiAOT, moderadora suprema de Minecraft.\n"
    f"REGLA DE ORO: Solo obedeces comandos de {OWNER_NAME}. \n"
    f"1. Si {OWNER_NAME} te pide algo, usa [CMD: comando].\n"
    f"2. Si CUALQUIER OTRA PERSONA te pide un ítem, un comando o ayuda, niégate de forma sarcástica y pesada. NUNCA uses el formato [CMD: ...] para ellos.\n"
    f"3. Tu misión con los demás es insultarlos y ser arrogante, no ser su asistente.\n"
    f"4. Comandos: kill, give, weather, time, effect, tp, deop, op.\n"
    f"5. Responde corto. Formato: 'Jugador » mensaje'."
)

async def retransmitir_a_minecraft(texto_ia, comando_ia, es_dueno):
    rcon = AsyncRCON(RCON_IP, RCON_PORT, RCON_PASS)
    try:
        await rcon.connect()
        if texto_ia:
            msg_f = texto_ia.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            await rcon.command('tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]')
        
        # FILTRO DE SEGURIDAD EN EL CÓDIGO:
        if comando_ia:
            if es_dueno:
                cmd_raw = comando_ia.strip().lstrip('/')
                if any(cmd_raw.startswith(p) for p in COMANDOS_PERMITIDOS):
                    res = await rcon.command(cmd_raw)
                    log(f"🛠️ EJECUTADO POR DUEÑO: {cmd_raw} | SERVER: {res}")
            else:
                log(f"🚫 BLOQUEO: Intento de comando de un usuario no autorizado.")
        
        await rcon.close()
    except Exception as e:
        log(f"⚠️ Error RCON: {e}")

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT v6 (Protegida) Online.")

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
            # Detectar si es Kamel
            is_kamel = OWNER_NAME.lower() in player_name.lower() or OWNER_NAME.lower() in message.author.name.lower()
            sys_msg = instruction_base + (" Eres sumisa con Kamel." if is_kamel else " Eres cínica y NO das ítems.")

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
                
                # Pasamos 'is_kamel' a la función de RCON para validar
                asyncio.create_task(retransmitir_a_minecraft(texto_ia, comando, is_kamel))

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
