"""Conecta el bot de Telegram con una ventana de macOS (el token no se muestra en ningún sitio)."""
import subprocess
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__file__))
from configurar import GH, run, tg  # noqa: E402


def dialogo(texto, oculto=False):
    script = 'text returned of (display dialog "%s" default answer "" %s with title "Radar Rioniverso" buttons {"Cancelar", "Aceptar"} default button "Aceptar")' % (
        texto.replace('"', '\\"'), "with hidden answer" if oculto else "")
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        print("Cancelado")
        sys.exit(1)
    return r.stdout.strip()


def aviso(texto):
    subprocess.run(["osascript", "-e", 'display dialog "%s" with title "Radar Rioniverso" buttons {"Hecho"} default button "Hecho" giving up after 170' % texto.replace('"', '\\"')],
                   capture_output=True)


token = dialogo("Pega aquí el token que te ha dado @BotFather en Telegram:", oculto=True)
try:
    bot = tg(token, "getMe")
except Exception:
    print("TOKEN_MAL")
    sys.exit(2)
print("Bot: @" + bot["username"])
tg(token, "deleteWebhook")
subprocess.run(["open", "https://t.me/%s" % bot["username"]])
chat = None
for _ in range(90):
    for u in tg(token, "getUpdates", timeout=5) or []:
        m = u.get("message") or {}
        if m.get("chat", {}).get("type") == "private":
            chat = m["chat"]["id"]
    if chat:
        break
    time.sleep(1)
if not chat:
    print("SIN_MENSAJE")
    sys.exit(3)
ultimos = tg(token, "getUpdates", timeout=0) or []
if ultimos:
    tg(token, "getUpdates", offset=ultimos[-1]["update_id"] + 1, timeout=0)
tg(token, "sendMessage", chat_id=chat, parse_mode="HTML",
   text="🛰️ <b>Radar Rioniverso conectado</b>\n\nA partir de ahora te aviso de cada noticia del espacio y "
        "de los lanzamientos (24 h y 1 h antes).\n\nEn cada aviso tienes botones: 🎬 Lo hago · ⭐ Guardar · "
        "🗑️ Descartar. Lo que marques aparece en tu panel.")
run(GH, "secret", "set", "TELEGRAM_TOKEN", entrada=token)
run(GH, "secret", "set", "TELEGRAM_CHAT_ID", entrada=str(chat))
print("TELEGRAM_OK")
