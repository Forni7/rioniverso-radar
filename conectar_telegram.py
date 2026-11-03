"""Conecta el bot de Telegram con ventanas de macOS. El token se guarda en el Llavero del Mac y en los secretos de GitHub."""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from configurar import GH, run, tg  # noqa: E402

LLAVERO = "rioniverso-radar-telegram"


def dialogo(texto):
    script = ('text returned of (display dialog "%s" default answer "" with title "Radar Rioniverso" '
              'buttons {"Cancelar", "Aceptar"} default button "Aceptar")') % texto.replace('"', '\\"')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        print("CANCELADO")
        sys.exit(1)
    return r.stdout.strip()


def aviso(texto):
    subprocess.Popen(["osascript", "-e", 'display dialog "%s" with title "Radar Rioniverso" buttons {"Vale"} '
                      'default button "Vale" giving up after 600' % texto.replace('"', '\\"')])


def bot_de(token):
    try:
        return tg(token, "getMe")
    except Exception:
        return None


# 1. Token: del Llavero si ya lo diste antes; si no, ventanita
r = subprocess.run(["security", "find-generic-password", "-s", LLAVERO, "-w"], capture_output=True, text=True)
token = r.stdout.strip() if r.returncode == 0 else ""
bot = bot_de(token) if token else None
for intento in range(3):
    if bot:
        break
    txt = dialogo(("Ese token no funcionó. " if intento else "") + "Pega aquí el token de @BotFather "
                  "(la línea larga tipo 123456789:AAH...). Puedes pegar el mensaje entero:")
    m = re.search(r"\d{6,}:[A-Za-z0-9_-]{30,}", txt)
    token = m.group(0) if m else txt.strip()
    bot = bot_de(token)
if not bot:
    print("TOKEN_MAL")
    sys.exit(2)
subprocess.run(["security", "add-generic-password", "-U", "-s", LLAVERO, "-a", "radar", "-w", token], capture_output=True)
run(GH, "secret", "set", "TELEGRAM_TOKEN", entrada=token)
print("Bot: @" + bot["username"], "· token guardado")

# 2. Esperar a que pulses INICIAR en el bot
tg(token, "deleteWebhook")
subprocess.run(["open", "https://t.me/%s?start=radar" % bot["username"]])
aviso("Se ha abierto tu bot @%s en Telegram. Pulsa INICIAR (o escríbele cualquier cosa, por ejemplo: hola)." % bot["username"])
chat = None
fin = time.time() + 15 * 60
while time.time() < fin and not chat:
    for u in tg(token, "getUpdates", timeout=20) or []:
        m = u.get("message") or {}
        if m.get("chat", {}).get("type") == "private":
            chat = m["chat"]["id"]
if not chat:
    print("SIN_MENSAJE")
    sys.exit(3)
ultimos = tg(token, "getUpdates", timeout=0) or []
if ultimos:
    tg(token, "getUpdates", offset=ultimos[-1]["update_id"] + 1, timeout=0)
run(GH, "secret", "set", "TELEGRAM_CHAT_ID", entrada=str(chat))
tg(token, "sendMessage", chat_id=chat, parse_mode="HTML",
   text="🛰️ <b>Radar Rioniverso conectado</b>\n\nA partir de ahora te aviso de cada noticia del espacio y "
        "de los lanzamientos (24 h y 1 h antes).\n\nEn cada aviso tienes botones: 🎬 Lo hago · ⭐ Guardar · "
        "🗑️ Descartar. Lo que marques aparece en tu panel:\nhttps://forni7.github.io/rioniverso-radar/")
print("TELEGRAM_OK")
