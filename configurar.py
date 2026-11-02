"""Asistente para activar el Radar Rioniverso. Ejecútalo tú en la Terminal:  python3 configurar.py

Hace todo: sube el radar a tu GitHub, conecta tu bot de Telegram, activa el panel web y lanza la primera búsqueda.
Tu token de Telegram solo lo ves tú: se escribe oculto y va directo a los secretos de GitHub.
"""
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = "rioniverso-radar"
GH = shutil.which("gh") or next((p for p in ("/usr/local/bin/gh", "/opt/homebrew/bin/gh", os.path.expanduser("~/.local/bin/gh"))
                                  if os.path.exists(p)), "")


def run(*cmd, entrada=None, ok=True):
    r = subprocess.run(cmd, cwd=AQUI, input=entrada, text=True, capture_output=True)
    if ok and r.returncode != 0:
        print("\n❌ Falló:", " ".join(cmd[:3]), "\n", r.stderr.strip() or r.stdout.strip())
        sys.exit(1)
    return r


def tg(token, metodo, **p):
    req = urllib.request.Request("https://api.telegram.org/bot%s/%s" % (token, metodo),
                                 data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())["result"]


def paso(n, t):
    print("\n\033[1m%s. %s\033[0m" % (n, t))


def main():
    print("🛰️  Configurando el Radar Rioniverso\n")

    paso(1, "GitHub")
    if not GH:
        print("Falta GitHub CLI. Se abre su web: pulsa 'Download for Mac', abre el archivo .pkg descargado,")
        print("sigue el instalador y vuelve a ejecutar:  python3 configurar.py")
        subprocess.run(["open", "https://cli.github.com"])
        sys.exit(1)
    if run(GH, "auth", "status", ok=False).returncode != 0:
        print("Vamos a iniciar sesión en GitHub (se abrirá el navegador; copia el código que salga aquí).")
        subprocess.run([GH, "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web",
                        "--scopes", "workflow"], cwd=AQUI)
        if run(GH, "auth", "status", ok=False).returncode != 0:
            print("❌ No se completó el inicio de sesión. Vuelve a ejecutar este asistente.")
            sys.exit(1)
    run(GH, "auth", "setup-git")
    usuario = run(GH, "api", "user", "--jq", ".login").stdout.strip()
    print("✅ Sesión iniciada como", usuario)

    if not os.path.isdir(os.path.join(AQUI, ".git")):
        run("git", "init", "-q", "-b", "main")
    run("git", "add", "-A")
    if run("git", "diff", "--cached", "--quiet", ok=False).returncode != 0:
        run("git", "-c", "user.name=" + usuario, "-c", "user.email=%s@users.noreply.github.com" % usuario,
            "commit", "-q", "-m", "Radar Rioniverso")
    existe = run(GH, "repo", "view", "%s/%s" % (usuario, REPO), ok=False).returncode == 0
    if not existe:
        run(GH, "repo", "create", REPO, "--public", "--source", ".", "--push",
            "--description", "Radar de noticias del espacio para Rioniverso")
        print("✅ Repositorio creado: https://github.com/%s/%s" % (usuario, REPO))
    else:
        if run("git", "remote", ok=False).stdout.strip() == "":
            run("git", "remote", "add", "origin", "https://github.com/%s/%s.git" % (usuario, REPO))
        run("git", "push", "-q", "-u", "origin", "main")
        print("✅ Repositorio actualizado")

    paso(2, "Telegram")
    print("En Telegram, abre @BotFather, escribe /newbot, ponle un nombre (ej. Radar Rioniverso)")
    print("y un usuario que acabe en 'bot' (ej. rioniverso_radar_bot). Te dará un token.")
    token = getpass.getpass("Pega aquí el token (no se verá al escribir) y pulsa Enter: ").strip()
    try:
        bot = tg(token, "getMe")
    except Exception:
        print("❌ Ese token no funciona. Revísalo en @BotFather y vuelve a ejecutar el asistente.")
        sys.exit(1)
    print("✅ Bot encontrado: @%s" % bot["username"])
    print("Ahora abre https://t.me/%s y pulsa INICIAR (o escribe /start). Te espero…" % bot["username"])
    chat = None
    tg(token, "deleteWebhook")
    for _ in range(60):
        for u in tg(token, "getUpdates", timeout=5) or []:
            m = u.get("message") or {}
            if m.get("chat", {}).get("type") == "private":
                chat = m["chat"]["id"]
        if chat:
            break
        time.sleep(2)
    if not chat:
        print("❌ No me llegó tu mensaje. Vuelve a ejecutar el asistente.")
        sys.exit(1)
    # vaciar la cola para que el radar empiece limpio
    ultimos = tg(token, "getUpdates", timeout=0) or []
    if ultimos:
        tg(token, "getUpdates", offset=ultimos[-1]["update_id"] + 1, timeout=0)
    tg(token, "sendMessage", chat_id=chat, parse_mode="HTML",
       text="🛰️ <b>Radar Rioniverso conectado</b>\n\nA partir de ahora te aviso de cada noticia del espacio y "
            "de los lanzamientos (24 h y 1 h antes).\n\nEn cada aviso tienes botones: 🎬 Lo hago · ⭐ Guardar · "
            "🗑️ Descartar. Lo que marques aparece en tu panel.")
    run(GH, "secret", "set", "TELEGRAM_TOKEN", entrada=token)
    run(GH, "secret", "set", "TELEGRAM_CHAT_ID", entrada=str(chat))
    print("✅ Telegram conectado (revisa tu móvil)")

    paso(3, "Panel web")
    r = run(GH, "api", "-X", "POST", "repos/%s/%s/pages" % (usuario, REPO),
            "-f", "source[branch]=main", "-f", "source[path]=/docs", ok=False)
    if r.returncode != 0 and "already" not in (r.stdout + r.stderr).lower():
        print("⚠️  No pude activar GitHub Pages solo:", (r.stdout + r.stderr).strip()[:200])
        print("   Actívalo en: https://github.com/%s/%s/settings/pages (rama main, carpeta /docs)" % (usuario, REPO))
    panel = "https://%s.github.io/%s/" % (usuario.lower(), REPO)
    print("✅ Panel:", panel, "(tarda 1-2 minutos la primera vez)")

    paso(4, "Primera búsqueda")
    run(GH, "workflow", "enable", "radar.yml", ok=False)
    run(GH, "workflow", "run", "radar.yml")
    print("✅ Radar en marcha. Desde ahora se ejecuta solo cada ~10 minutos, aunque apagues el Mac.")
    print("\n🎉 ¡Listo! Guarda el panel en la pantalla de inicio del móvil:", panel)


if __name__ == "__main__":
    main()
