"""Piezas compartidas por los portales: cliente HTTP prudente y formato común de anuncio."""
import random
import re
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
IDIOMA = {"ES": "es-ES,es;q=0.9", "DE": "de-DE,de;q=0.9"}


class Bloqueado(Exception):
    """El portal rechaza las peticiones: se deja de consultar ese portal hoy."""


class Cliente:
    def __init__(self, pausa, marcas_bloqueo=(), reintentos=3):
        self.pausa = pausa
        self.marcas_bloqueo = marcas_bloqueo
        self.reintentos = reintentos
        self.peticiones = 0

    def get(self, url, pais="ES"):
        error = None
        for intento in range(self.reintentos):
            time.sleep(random.uniform(*self.pausa))
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": IDIOMA.get(pais, IDIOMA["ES"]),
                })
                with urllib.request.urlopen(req, timeout=25) as r:
                    html = r.read().decode("utf-8", "replace")
                self.peticiones += 1
            except urllib.error.HTTPError as e:
                if e.code in (404, 410):
                    return None
                if e.code in (403, 429):
                    raise Bloqueado(f"HTTP {e.code}")
                error = e
            except Exception as e:  # red intermitente, timeouts...
                error = e
            else:
                if any(m in html for m in self.marcas_bloqueo):
                    raise Bloqueado("página anti-bots")
                return html
            time.sleep(2 ** intento * 3)
        print(f"    ! sin respuesta: {url} ({error})", flush=True)
        return None


def modelo_norm(nombre):
    """'Serie 3', '3 Series', '3er' -> '3';  'Clase C', 'C-Class' -> 'c';  'CX-5' -> 'cx5'."""
    n = (nombre or "").lower()
    n = re.sub(r"\b(series|serie|class|clase|klasse|reihe)\b", " ", n)
    n = re.sub(r"\b(\d)er\b", r"\1", n)
    return re.sub(r"[^a-z0-9]", "", n) or "?"


def anuncio(**campos):
    base = {
        "id": None, "fuente": None, "pais": None, "url": "", "marca": "", "grupo": "",
        "titulo": "", "version": "", "precio": None, "km": None, "matriculacion": None,
        "kw": None, "combustible": "", "electrico": False, "cambio": "", "ciudad": "",
        "vendedor": "", "imagen": "", "publicado": None, "publicado_hoy": None,
        "garantia_meses": None, "mediana_portal": None, "co2": None, "bajada_portal": 0,
        "etiqueta": "",
    }
    base.update(campos)
    base["modelo_norm"] = modelo_norm(base["grupo"])
    base["electrico"] = bool(base["electrico"]) or bool(
        re.search(r"eléctrico|elektro|electric", base["combustible"], re.I)
        and not re.search(r"h[ií]brid", base["combustible"], re.I))
    return base


def entero(texto):
    """'23.499 €' -> 23499"""
    d = re.sub(r"[^\d]", "", str(texto or ""))
    return int(d) if d else None
