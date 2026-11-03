"""Radar Rioniverso: vigila noticias y lanzamientos, avisa por Telegram y guarda todo en docs/datos.

Se ejecuta cada ~10 min en GitHub Actions (y se puede probar en local con --prueba).
Solo usa la biblioteca estándar de Python.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(__file__))
import fuentes  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "docs", "datos")
F_NOTICIAS = os.path.join(DATOS, "noticias.json")
F_LANZ = os.path.join(DATOS, "lanzamientos.json")
F_ANALISIS = os.path.join(DATOS, "analisis.json")
F_ESTADO = os.path.join(DATOS, "estado.json")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
MAX_NOTICIAS = 2000
DIAS_GUARDADOS = 45


def ahora():
    return dt.datetime.now(dt.timezone.utc)


def hora_madrid(t):
    # Horario de verano europeo: último domingo de marzo a último domingo de octubre (01:00 UTC)
    def ultimo_domingo(año, mes):
        d = dt.datetime(año, mes, 31 if mes in (3, 10) else 30, 1, tzinfo=dt.timezone.utc)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    verano = ultimo_domingo(t.year, 3) <= t < ultimo_domingo(t.year, 10)
    return t.astimezone(dt.timezone(dt.timedelta(hours=2 if verano else 1)))


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def guardar_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def descargar(url, timeout=25, datos=None):
    req = urllib.request.Request(url, data=datos, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------- Feeds ----------

def texto_limpio(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def local(tag):
    return tag.rsplit("}", 1)[-1]


def fecha_de(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def leer_feed(nombre, url, oficial):
    try:
        crudo = descargar(url)
    except Exception as e:  # una fuente caída no debe parar el radar
        print("  ✗", nombre, url, type(e).__name__, e)
        return []
    try:
        raiz = ET.fromstring(crudo)
    except ET.ParseError:
        # Algunos feeds traen '&' sueltos, caracteres de control o entidades HTML: se limpian y se reintenta
        txt = crudo.decode("utf-8", "replace")
        txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", txt)
        txt = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", txt)
        txt = re.sub(r'"(xmlns:\w+=")', r'" \1', txt)  # NASA Ciencia: atributos pegados
        # JPL: <content:encoded<![CDATA[ … ]]>/>  →  <content:encoded><![CDATA[ … ]]></content:encoded>
        txt = re.sub(r"<([\w:]+)<!\[CDATA\[(.*?)\]\]>/>", r"<\1><![CDATA[\2]]></\1>", txt, flags=re.S)
        try:
            raiz = ET.fromstring(txt.encode("utf-8"))
        except ET.ParseError as e:
            print("  ✗", nombre, url, "formato no válido:", e, "| empieza por:", txt[:80].replace("\n", " "))
            return []
    items = []
    for el in raiz.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        d = {"titulo": "", "url": "", "desc": "", "fecha": None, "img": ""}
        for h in el:
            t = local(h.tag)
            if t == "title":
                d["titulo"] = texto_limpio(h.text)
            elif t == "link":
                valor = (h.get("href") or h.text or "").strip()
                if valor and not d["url"] and h.get("rel", "alternate") == "alternate":
                    d["url"] = valor
            elif t in ("description", "summary") and not d["desc"]:
                d["desc"] = texto_limpio(h.text)
            elif t == "encoded" and not d["desc"]:
                d["desc"] = texto_limpio(h.text)
            elif t in ("pubDate", "published", "updated", "date") and not d["fecha"]:
                d["fecha"] = fecha_de(h.text)
            elif t in ("content", "thumbnail", "enclosure") and not d["img"]:
                u = h.get("url") or ""
                if re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I) or "image" in (h.get("type") or h.get("medium") or ""):
                    d["img"] = u
        if not d["titulo"] or not d["url"]:
            continue
        # Google Noticias pone " - Medio" al final del título
        fuente = nombre
        if "news.google.com" in url and " - " in d["titulo"]:
            d["titulo"], medio = d["titulo"].rsplit(" - ", 1)
            fuente = medio.strip()
        d.update(fuente=fuente, oficial=oficial)
        items.append(d)
    return items


# ---------- Clasificación ----------

def contiene(texto, palabra):
    return re.search(r"(?<![a-záéíóúñ])" + re.escape(palabra.strip()), texto) is not None


def clasificar(titulo, desc):
    t = " " + (titulo + " " + desc).lower() + " "
    for clave, etiqueta, palabras in fuentes.CATEGORIAS:
        if any(contiene(t, p) for p in palabras):
            return clave, etiqueta
    return fuentes.CATEGORIA_DEFECTO


def puntuar(item):
    t = (item["titulo"] + " " + item["desc"][:300]).lower()
    p = 3 if item["oficial"] else 1
    p += min(4, sum(2 for k in fuentes.IMPACTO if contiene(" " + t, k)))
    if item["cat"] == "es":
        p += 3
    if item["cat"] in ("starship", "luna"):
        p += 1
    return p


def excluida(titulo):
    t = titulo.lower()
    return any(k in t for k in fuentes.EXCLUIR)


def silenciosa(titulo):
    t = titulo.lower()
    return any(k in t for k in fuentes.SILENCIOSAS)


def palabras_clave(titulo):
    vacias = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "with", "its", "is", "at", "by", "from",
              "as", "new", "after", "how", "what", "why", "la", "el", "de", "en", "y", "los", "las", "un", "una"}
    return {w for w in re.findall(r"[a-z0-9áéíóúñ]+", titulo.lower()) if len(w) > 2 and w not in vacias}


def misma_noticia(a, b):
    sa, sb = palabras_clave(a), palabras_clave(b)
    if not sa or not sb:
        return False
    return len(sa & sb) / min(len(sa), len(sb)) >= 0.6 and len(sa & sb) >= 3


# ---------- Traducción (gratuita, sin clave) ----------

def traducir(texto):
    if not texto:
        return ""
    if re.search(r"[áéíóúñ¿¡]", texto):  # ya está en español
        return texto
    try:
        url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=es&dt=t&q="
               + urllib.parse.quote(texto[:1500]))
        r = json.loads(descargar(url, timeout=15))
        return "".join(p[0] for p in r[0] if p and p[0]).strip() or texto
    except Exception:
        return texto


# ---------- Telegram ----------

def tg(metodo, **params):
    if not TOKEN:
        return None
    datos = json.dumps(params).encode()
    req = urllib.request.Request("https://api.telegram.org/bot%s/%s" % (TOKEN, metodo), data=datos,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("result")
    except Exception as e:
        print("  ✗ Telegram", metodo, e)
        return None


def url_panel():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        dueño, nombre = repo.split("/", 1)
        return "https://%s.github.io/%s/" % (dueño.lower(), nombre)
    return os.environ.get("PANEL_URL", "")


ESTADOS = {"hago": "🎬 Lo hago", "fav": "⭐ Guardada", "desc": "🗑️ Descartada"}


def botones(nid, estado="nuevo"):
    fila = []
    for clave, texto in ESTADOS.items():
        marca = "✅ " if estado == clave else ""
        fila.append({"text": marca + texto, "callback_data": "e:%s:%s" % (clave, nid)})
    teclado = [fila]
    panel = url_panel()
    if panel:
        teclado.append([{"text": "📊 Abrir panel", "url": panel + "#" + nid}])
    return {"inline_keyboard": teclado}


def e(s):
    return html.escape(s or "", quote=False)


def avisar_noticia(n):
    hora = hora_madrid(dt.datetime.fromisoformat(n["t"])).strftime("%H:%M")
    fuego = "🔥 " if n["imp"] >= 7 else ""
    resumen = n.get("resumen_es", "")
    if len(resumen) > 280:
        resumen = resumen[:277].rsplit(" ", 1)[0] + "…"
    texto = "%s<b>%s</b>\n%s\n\n%s\n\n📰 %s · %s\n%s" % (
        fuego, e(n["cat_txt"]), "<b>" + e(n["titulo_es"]) + "</b>", e(resumen), e(n["fuente"]),
        hora + " h", '<a href="%s">Leer la noticia</a>' % e(n["url"]))
    msg = tg("sendMessage", chat_id=CHAT, text=texto, parse_mode="HTML",
             disable_notification=n.get("silencio", False), reply_markup=botones(n["id"]),
             link_preview_options={"url": n["url"], "prefer_small_media": True})
    return msg and msg.get("message_id")


def procesar_botones(estado, noticias):
    """Lee los botones pulsados en Telegram y actualiza el estado de cada noticia."""
    if not TOKEN:
        return
    upd = tg("getUpdates", offset=estado.get("tg_offset", 0), timeout=0, allowed_updates=["callback_query"]) or []
    por_id = {n["id"]: n for n in noticias}
    for u in upd:
        estado["tg_offset"] = u["update_id"] + 1
        q = u.get("callback_query")
        if not q or str(q.get("message", {}).get("chat", {}).get("id")) != str(CHAT):
            continue
        partes = (q.get("data") or "").split(":")
        if len(partes) != 3 or partes[0] != "e":
            continue
        _, clave, nid = partes
        n = por_id.get(nid)
        if not n:
            continue
        n["estado"] = "nuevo" if n.get("estado") == clave else clave  # pulsar otra vez lo quita
        n["estado_t"] = ahora().isoformat()
        tg("answerCallbackQuery", callback_query_id=q["id"], text=ESTADOS.get(n["estado"], "Quitado"))
        tg("editMessageReplyMarkup", chat_id=CHAT, message_id=q["message"]["message_id"],
           reply_markup=botones(nid, n["estado"]))


# ---------- Lanzamientos ----------

def actualizar_lanzamientos(estado, avisar):
    try:
        d = json.loads(descargar("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=40&mode=detailed",
                                 timeout=40))
    except Exception as ex:
        print("  ✗ lanzamientos", ex)
        return
    lista = []
    for l in d.get("results", []):
        vids = [v.get("url") for v in (l.get("vid_urls") or l.get("vidURLs") or []) if v.get("url")]
        mision = l.get("mission") or {}
        img = l.get("image") or {}
        lista.append({
            "id": l["id"], "nombre": l["name"], "net": l["net"], "precision": (l.get("net_precision") or {}).get("name", ""),
            "estado": (l.get("status") or {}).get("abbrev", ""),
            "estado_txt": (l.get("status") or {}).get("name", ""),
            "proveedor": (l.get("launch_service_provider") or {}).get("name", ""),
            "cohete": ((l.get("rocket") or {}).get("configuration") or {}).get("full_name", ""),
            "lugar": ((l.get("pad") or {}).get("location") or {}).get("name", ""),
            "mision": mision.get("description", ""), "orbita": (mision.get("orbit") or {}).get("abbrev", ""),
            "prob": l.get("probability"), "videos": vids[:3],
            "img": img.get("thumbnail_url") or img.get("image_url") if isinstance(img, dict) else img,
            "starlink": "starlink" in l["name"].lower(),
        })
    guardar_json(F_LANZ, {"actualizado": ahora().isoformat(), "lista": lista})

    avisados = estado.setdefault("lanz_avisados", {})
    for l in lista:
        if l["starlink"] or l["estado"] not in ("Go", "TBC", "TBD"):
            continue
        try:
            net = dt.datetime.fromisoformat(l["net"].replace("Z", "+00:00"))
        except ValueError:
            continue
        horas = (net - ahora()).total_seconds() / 3600
        hechos = avisados.setdefault(l["id"], [])
        tipo = None
        if 0 < horas <= 1.3 and "1h" not in hechos and l["estado"] == "Go":
            tipo = "1h"
        elif 2 < horas <= 24 and "24h" not in hechos:
            tipo = "24h"
        if not tipo:
            continue
        hechos.append(tipo)
        if not avisar:
            continue
        cuando = hora_madrid(net).strftime("%d/%m a las %H:%M h")
        cab = "🔴 <b>DESPEGA EN MENOS DE 1 HORA</b>" if tipo == "1h" else "🚀 <b>Lanzamiento en las próximas 24 h</b>"
        vid = '\n📺 <a href="%s">Directo</a>' % e(l["videos"][0]) if l["videos"] else ""
        mis = l["mision"][:220] + ("…" if len(l["mision"]) > 220 else "")
        texto = "%s\n\n<b>%s</b>\n%s · %s\n🕒 %s (hora de Madrid)\n📍 %s\n\n%s%s" % (
            cab, e(l["nombre"]), e(l["proveedor"]), e(l["cohete"]), cuando, e(l["lugar"]), e(traducir(mis)), vid)
        tg("sendMessage", chat_id=CHAT, text=texto, parse_mode="HTML",
           link_preview_options={"is_disabled": True})
    # limpiar los que ya pasaron
    vivos = {l["id"] for l in lista}
    estado["lanz_avisados"] = {k: v for k, v in avisados.items() if k in vivos}


# ---------- Análisis de Claude ----------

def avisar_analisis(estado, noticias, avisar):
    analisis = leer_json(F_ANALISIS, {})
    hechos = set(estado.get("analisis_avisados", []))
    por_id = {n["id"]: n for n in noticias}
    for nid, a in analisis.items():
        if nid in hechos:
            continue
        hechos.add(nid)
        if not avisar or (a.get("potencial") or 0) < 7:
            continue
        n = por_id.get(nid, {})
        verif = {"confirmado": "✅ Confirmado", "anunciado": "🟡 Anunciado", "rumor": "⚠️ Rumor"}.get(a.get("verificacion"), "")
        texto = "🧠 <b>Idea de vídeo · potencial %s/10</b>\n\n<b>%s</b>\n%s\n\n💬 <i>%s</i>\n\n🎨 %s\n⏳ %s" % (
            a.get("potencial"), e(a.get("titular") or n.get("titulo_es", "")), verif, e(a.get("gancho", "")),
            e(a.get("grafismos", "")), e(a.get("caducidad", "")))
        tg("sendMessage", chat_id=CHAT, text=texto, parse_mode="HTML", reply_markup=botones(nid, n.get("estado", "nuevo")))
    estado["analisis_avisados"] = sorted(hechos)[-3000:]


# ---------- Principal ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true", help="no envía nada a Telegram")
    args = ap.parse_args()
    avisar = bool(TOKEN and CHAT) and not args.prueba

    noticias = leer_json(F_NOTICIAS, [])
    estado = leer_json(F_ESTADO, {})
    primera_vez = not estado.get("iniciado")

    if avisar:
        procesar_botones(estado, noticias)

    t0 = time.time()
    with ThreadPoolExecutor(12) as p:
        lotes = list(p.map(lambda f: leer_feed(*f), fuentes.FEEDS))
    brutos = [i for lote in lotes for i in lote]
    print("Leídas %d entradas de %d fuentes en %.1fs" % (len(brutos), len(fuentes.FEEDS), time.time() - t0))

    vistas = {n["url"] for n in noticias} | set(estado.get("urls_vistas", []))
    limite = ahora() - dt.timedelta(days=3)
    recientes = [n for n in noticias if dt.datetime.fromisoformat(n["t"]) > ahora() - dt.timedelta(hours=48)]
    nuevas = []
    for b in sorted(brutos, key=lambda x: x["fecha"] or ahora()):
        if b["url"] in vistas:
            continue
        vistas.add(b["url"])
        if excluida(b["titulo"]) or (b["fecha"] and b["fecha"] < limite):
            continue
        # ¿es la misma historia que otra reciente? Se añade como fuente extra y no se avisa otra vez
        repe = next((n for n in recientes + nuevas if misma_noticia(n["titulo"], b["titulo"])), None)
        if repe:
            if b["fuente"] not in [f["n"] for f in repe["fuentes"]]:
                repe["fuentes"].append({"n": b["fuente"], "u": b["url"]})
                repe["imp"] = repe["imp"] + 1
            continue
        cat, cat_txt = clasificar(b["titulo"], b["desc"])
        n = {
            "id": hashlib.sha1(b["url"].encode()).hexdigest()[:10],
            "t": (b["fecha"] or ahora()).isoformat(), "visto": ahora().isoformat(),
            "titulo": b["titulo"], "url": b["url"], "fuente": b["fuente"], "oficial": b["oficial"],
            "fuentes": [{"n": b["fuente"], "u": b["url"]}], "desc": b["desc"][:600], "img": b["img"],
            "cat": cat, "cat_txt": cat_txt, "estado": "nuevo",
        }
        n["imp"] = puntuar(n)
        n["silencio"] = silenciosa(b["titulo"])
        nuevas.append(n)

    print("Noticias nuevas:", len(nuevas), "(primera vez: solo se guardan)" if primera_vez else "")
    with ThreadPoolExecutor(8) as p:
        tit = list(p.map(lambda n: traducir(n["titulo"]), nuevas))
        res = list(p.map(lambda n: traducir(n["desc"][:450]), nuevas))
    for n, a, b in zip(nuevas, tit, res):
        n["titulo_es"], n["resumen_es"] = a, b

    for n in nuevas:
        if avisar and not primera_vez:
            n["tg"] = avisar_noticia(n)
            time.sleep(1.1)  # Telegram: ~1 mensaje por segundo
        print("  +", n["imp"], n["cat_txt"], "|", n["titulo_es"][:90])

    noticias = nuevas[::-1] + noticias
    corte = ahora() - dt.timedelta(days=DIAS_GUARDADOS)
    noticias = [n for n in noticias if dt.datetime.fromisoformat(n["t"]) > corte or n.get("estado") in ("hago", "fav")]
    noticias.sort(key=lambda n: n["t"], reverse=True)
    noticias = noticias[:MAX_NOTICIAS]
    guardar_json(F_NOTICIAS, noticias)

    actualizar_lanzamientos(estado, avisar and not primera_vez)
    avisar_analisis(estado, noticias, avisar and not primera_vez)

    estado["iniciado"] = True
    estado["ultima"] = ahora().isoformat()
    estado["urls_vistas"] = list(vistas)[-6000:]
    guardar_json(F_ESTADO, estado)


if __name__ == "__main__":
    main()
