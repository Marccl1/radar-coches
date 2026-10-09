"""Aviso por Telegram con las mejores oportunidades del día.

Lee docs/oportunidades.json (lo genera rastreador.py) y manda un mensaje por
coche que supere el descuento mínimo del aviso y que no se haya avisado antes.

Necesita dos variables de entorno (en GitHub: Settings → Secrets → Actions):
    TELEGRAM_TOKEN    token del bot que te da @BotFather
    TELEGRAM_CHAT_ID  tu id de Telegram (te lo dice @userinfobot)

Uso:
    python avisar.py            # avisa de las oportunidades del día
    python avisar.py --prueba   # manda un mensaje de prueba para comprobar la configuración
    python avisar.py --error URL  # avisa de que el rastreo ha fallado
"""
import argparse
import html
import json
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
DATOS = RAIZ / "docs" / "oportunidades.json"
AVISADOS = RAIZ / "data" / "avisados.json"


def url_informe():
    """https://<usuario>.github.io/<repo>/ cuando corre en GitHub Actions."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return ""
    usuario, nombre = repo.split("/", 1)
    return f"https://{usuario.lower()}.github.io/{nombre}/"


class Telegram:
    def __init__(self, token, chat_id):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.chat_id = chat_id

    def _llamar(self, metodo, **datos):
        cuerpo = urllib.parse.urlencode({"chat_id": self.chat_id, **datos}).encode()
        try:
            with urllib.request.urlopen(self.base + metodo, cuerpo, timeout=30) as r:
                return json.load(r).get("ok", False)
        except urllib.error.HTTPError as e:
            print(f"  Telegram {metodo}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}")
            return False
        except Exception as e:  # sin red: no debe hacer fallar el rastreo
            print(f"  Telegram {metodo}: {e!r}")
            return False

    def mensaje(self, texto):
        return self._llamar("sendMessage", text=texto, parse_mode="HTML", disable_web_page_preview="true")

    def foto(self, url, texto):
        """Foto con texto; si Telegram no acepta la imagen, solo el texto."""
        if url and self._llamar("sendPhoto", photo=url, caption=texto, parse_mode="HTML"):
            return True
        return self.mensaje(texto)


def eur(n):
    return f"{n:,.0f} €".replace(",", ".") if n is not None else "–"


def texto_coche(o):
    e = html.escape
    mejor = max(x for x in (o.get("descuento"), o.get("ahorro_import"), -1) if x is not None)
    importando = (o.get("ahorro_import") or -1) > (o.get("descuento") or -1)
    lineas = [
        f"<b>{e(o['titulo'])}</b> · {o['pais']} · {e(o['fuente'])}",
        f"💶 <b>{eur(o['precio'])}</b>  (−{round(mejor * 100)} %{' importando' if importando else ''})",
        f"📅 {o['matriculacion'][:4]} · {o['km']:,} km".replace(",", ".")
        + (f" · {round(o['kw'] * 1.36)} CV" if o.get("kw") else ""),
        f"🛡️ Garantía {o['garantia_meses']} meses · {e(o.get('vendedor') or '')}",
    ]
    referencia = o.get("mediana_portal") or o.get("esperado")
    if referencia:
        lineas.append(f"📊 Mercado ~{eur(referencia)}")
    if o.get("importacion") and o.get("esperado_es"):
        lineas.append(f"🚚 Puesto en España {eur(o['importacion']['total'])} · aquí ~{eur(o['esperado_es'])}")
    if o.get("bajada"):
        lineas.append(f"📉 Ha bajado {eur(o['bajada'])}")
    if o.get("sospechoso"):
        lineas.append("⚠️ Precio muy bajo: revisar con cuidado")
    lineas.append(f'<a href="{e(o["url"])}">Ver anuncio</a>')
    return "\n".join(lineas)


def resumen_dia(r, n_informe, minimo, informe):
    """Mensaje de los días sin novedades: confirma que el rastreo ha corrido y cómo han ido los portales."""
    lineas = [f"🔍 <b>Rastreo hecho</b>: nada nuevo por encima del {round(minimo * 100)} % hoy."]
    if r.get("analizados"):
        lineas.append(f"Analizados {r['analizados']:,} anuncios".replace(",", ".")
                      + f", {r.get('publicados_hoy', 0)} publicados en las últimas horas.")
    if n_informe:
        lineas.append(f"En el informe hay {n_informe} con descuento menor o ya avisadas.")
    for portal, estado in (r.get("portales") or {}).items():
        lineas.append(f"{'🟢' if estado.startswith('OK') else '🔴'} {html.escape(portal)}: {html.escape(estado)}")
    if informe:
        lineas.append(f'<a href="{informe}">Ver informe</a>')
    return "\n".join(lineas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--error", metavar="URL")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Aviso por Telegram no configurado (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID). Se omite.")
        return
    tg = Telegram(token.strip(), chat_id.strip())

    if args.prueba:
        ok = tg.mensaje("✅ <b>Radar de chollos</b> conectado. Aquí recibirás las oportunidades del día.")
        print("Mensaje de prueba enviado." if ok else "No se pudo enviar: revisa el token y el chat id.")
        sys.exit(0 if ok else 1)
    if args.error:
        tg.mensaje(f'❌ <b>El rastreo de hoy ha fallado.</b>\n<a href="{html.escape(args.error)}">Ver el error en GitHub</a>')
        return

    cfg = tomllib.loads((RAIZ / "config.toml").read_text(encoding="utf-8")).get("aviso", {})
    minimo = cfg.get("descuento_minimo", 0.12)
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    avisados = json.loads(AVISADOS.read_text(encoding="utf-8")) if AVISADOS.exists() else []

    def mejor(o):
        return max(x for x in (o.get("descuento"), o.get("ahorro_import"), -1) if x is not None)

    nuevos = [o for o in datos["oportunidades"] if o["id"] not in avisados and mejor(o) >= minimo]
    informe = url_informe()
    if not nuevos:
        print("Nada nuevo que avisar.")
        if cfg.get("avisar_si_no_hay"):
            tg.mensaje(resumen_dia(datos.get("resumen") or {}, len(datos["oportunidades"]), minimo, informe))
        return

    mostrar = nuevos[:cfg.get("max_coches", 5)]
    cabecera = f"🚗 <b>{len(nuevos)} oportunidad{'es' if len(nuevos) != 1 else ''} nueva{'s' if len(nuevos) != 1 else ''}</b>"
    if len(nuevos) > len(mostrar):
        cabecera += f" (te enseño las {len(mostrar)} mejores)"
    if informe:
        cabecera += f'\n<a href="{informe}">Ver informe completo</a>'
    tg.mensaje(cabecera)
    for o in mostrar:
        tg.foto(o.get("imagen"), texto_coche(o))

    avisados += [o["id"] for o in nuevos]
    AVISADOS.parent.mkdir(exist_ok=True)
    AVISADOS.write_text(json.dumps(avisados[-3000:]), encoding="utf-8")
    print(f"Avisadas {len(mostrar)} de {len(nuevos)} oportunidades nuevas.")


if __name__ == "__main__":
    main()
