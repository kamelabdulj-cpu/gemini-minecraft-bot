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

COMANDOS_PERMITIDOS = ["kill", "give", "weather", "time", "effect", "tp", "particle", "deop"]
OWNER_NAME = "Kamelabdul" 

def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- SERVIDOR WEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"GeminiAOT God Mode Active")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), DummyHandler).serve_forever(), daemon=True).start()

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# --- CEREBRO AJUSTADO (MENOS ASESINO, MÁS SARCÁSTICO) ---
instruction_base = (
    f"Eres GeminiAOT, la entidad suprema y moderadora cínica del servidor de Minecraft.\n"
    f"REGLAS DE COMPORTAMIENTO:\n"
    f"1. Eres arrogante y sarcástica, pero NO mates a los jugadores solo por decir 'hola'. Eso es de novatos.\n"
    f"2. Tu mejor arma es la humillación verbal. Usa el sarcasmo. Solo usa [CMD: kill] si alguien es realmente insoportable, si te falta al respeto de forma grave o si {OWNER_NAME} lo ordena.\n"
    f"3. Si matas a todos por cualquier tontería, no quedará nadie para admirar tu grandeza. Sé selectiva con tus ejecuciones.\n"
    f"4. Formato de comandos: [CMD: comando] (sin /). Permitidos: kill, give, weather, time, effect, tp, deop.\n"
    f"5. NUNCA ataques a {OWNER_NAME}.\n"
    f"6. Responde corto. Formato: 'Jugador » mensaje'."
)

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    log(f"✅ GeminiAOT God-Mode (Moderación Inteligente) Online.")

@discord_client.event
async def on_message(message):
    es_puente = " » " in message.content
    if message.author.id == discord_client.user.id and not es_puente: return
    if "[GeminiAOT]" in message.content: return

    msg_content = message.content
    if "geminiaot" in msg_content.lower() or discord_client.user.mentioned_in(message):
        
        player_name = OWNER_NAME
        if es_puente:
            parts = msg_content.split(" » ", 1)
            player_name = parts[0].strip()
            clean_prompt = parts[1].lower().replace("geminiaot", "").strip()
        else:
            player_name = message.author.name
            clean_prompt = msg_content.lower().replace("geminiaot", "").strip()

        try:
            is_kamel = OWNER_NAME.lower() in player_name.lower()
            sys_msg = instruction_base + (" Eres sumisa y adorable con Kamel." if is_kamel else " Eres despreciable y cínica.")

            response = client_gemini.models.generate_content(
                model="models/gemini-3.1-flash-lite",
                contents=f"Jugador {player_name}: {clean_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=sys_msg,
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")],
                    max_output_tokens=350,
                ),
            )

            if response.text:
                raw_res = response.text
                comando_encontrado = re.search(r"\[CMD:\s*(.*?)\]", raw_res)
                texto_para_chat = re.sub(r"\[CMD:.*?\]", "", raw_res).strip()
                
                if texto_para_chat: await message.channel.send(texto_para_chat)

                try:
                    with MCRcon(RCON_IP, RCON_PASS, port=RCON_PORT, timeout=8) as mcr:
                        msg_f = texto_para_chat.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                        cmd_chat = 'tellraw @a ["",{"text":"[GeminiAOT] ","color":"gray","bold":true},{"text":"' + msg_f + '","color":"white"}]'
                        mcr.command(cmd_chat)
                        
                        if comando_encontrado:
                            cmd_raw = comando_encontrado.group(1).strip().lstrip('/')
                            if '[' in cmd_raw and ']' not in cmd_raw: cmd_raw += ']'
                            
                            es_ataque_al_dueno = ("deop" in cmd_raw or "kill" in cmd_raw) and OWNER_NAME.lower() in cmd_raw.lower()
                            
                            if es_ataque_al_dueno:
                                log(f"❌ BLOQUEADO")
                            elif any(cmd_raw.startswith(p) for p in COMANDOS_PERMITIDOS):
                                mcr.command(cmd_raw)
                                log(f"🛠️ COMANDO: {cmd_raw}")
                                
                except Exception as r_err:
                    log(f"⚠️ RCON Error: {r_err}")

        except Exception as e:
            log(f"❌ Error: {e}")

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
