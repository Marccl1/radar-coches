"""Cliente de AutoScout24 (España y Alemania): listados y fichas de detalle.

Lee el JSON que la web incrusta en cada página (__NEXT_DATA__). Hace pocas
peticiones, con pausas, y se detiene si el sitio empieza a rechazarlas.
"""
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

DOMINIOS = {"ES": "https://www.autoscout24.es", "DE": "https://www.autoscout24.de"}
CODIGO_PAIS = {"ES": "E", "DE": "D"}
IDIOMA = {"ES": "es-ES,es;q=0.9", "DE": "de-DE,de;q=0.9"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


class Bloqueado(Exception):
    """El sitio está rechazando peticiones (403/429): mejor parar."""


class Cliente:
    def __init__(self, pausa=(1.5, 3.5), reintentos=4):
        self.pausa = pausa
        self.reintentos = reintentos
        self.peticiones = 0
        self.rechazos = 0

    def _pagina(self, url, pais):
        error = None
        for intento in range(self.reintentos):
            time.sleep(random.uniform(*self.pausa))
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": IDIOMA[pais],
                })
                with urllib.request.urlopen(req, timeout=20) as r:
                    html = r.read().decode("utf-8", "replace")
                self.peticiones += 1
                m = _NEXT.search(html)
                if not m:
                    raise ValueError("página sin __NEXT_DATA__")
                return json.loads(m.group(1))["props"]["pageProps"]
            except urllib.error.HTTPError as e:
                if e.code in (404, 410):
                    return None
                if e.code in (403, 429):
                    self.rechazos += 1
                    if self.rechazos >= 6:
                        raise Bloqueado(f"HTTP {e.code} repetido en {url}")
                error = e
            except Exception as e:  # red intermitente, timeouts...
                error = e
            time.sleep(2 ** intento * 2)
        print(f"  ! sin respuesta: {url} ({error})")
        return None

    # ---------------------------------------------------------------- listados
    def buscar(self, pais, marca, busqueda, pagina):
        params = {
            "atype": "C", "custtype": "D", "cy": CODIGO_PAIS[pais],
            "offer": "U,J,D", "ustate": "N,U",
            "sort": "age", "desc": "1", "page": str(pagina),
            "fregfrom": str(busqueda["anio_desde"]), "kmto": str(busqueda["km_max"]),
            "pricefrom": str(busqueda["precio_min"]), "priceto": str(busqueda["precio_max"]),
        }
        params.update({k: str(v) for k, v in busqueda.get("extra", {}).items()})
        url = f"{DOMINIOS[pais]}/lst/{marca}?{urllib.parse.urlencode(params)}"
        pp = self._pagina(url, pais)
        if not pp:
            return [], 0
        anuncios = [a for a in (_anuncio(l, pais) for l in pp.get("listings", [])) if a]
        return anuncios, pp.get("numberOfPages") or 0

    # ------------------------------------------------------------------ fichas
    def detalle(self, anuncio):
        pp = self._pagina(anuncio["url"], anuncio["pais"])
        if not pp:
            return None
        d = pp.get("listingDetails") or {}
        v = d.get("vehicle") or {}
        publico = (d.get("prices") or {}).get("public") or {}
        texto = str(d.get("warranty") or "")
        m = re.search(r"\d+", texto)
        meses = int(m.group()) if m else (12 if d.get("warrantyExists") else 0)
        if not d.get("warrantyExists") and not m:
            meses = 0
        return {
            "activo": d.get("status", "Active") == "Active",
            "garantia_meses": meses,
            "garantia_texto": texto,
            "mediana_as24": publico.get("median"),
            "co2": (v.get("co2emissionInGramPerKmWithFallback") or {}).get("raw"),
            "carroceria": v.get("bodyType"),
            "color": v.get("bodyColor"),
            "traccion": v.get("driveTrain"),
        }


def _int(x):
    try:
        return int(str(x).replace(".", "").strip())
    except (TypeError, ValueError):
        return None


def _anuncio(l, pais):
    v = l.get("vehicle") or {}
    t = l.get("tracking") or {}
    precio = (l.get("price") or {}).get("priceRaw") or _int(t.get("price"))
    km = _int(t.get("mileage"))
    m = re.match(r"(\d{1,2})-(\d{4})", t.get("firstRegistration") or "")
    if not precio or km is None or not m:
        return None
    kw = None
    for det in l.get("vehicleDetails") or []:
        if det.get("iconName") == "speedometer":
            mk = re.search(r"(\d+)\s*kW", det.get("data") or "")
            kw = int(mk.group(1)) if mk else None
    loc = l.get("location") or {}
    vendedor = l.get("seller") or {}
    combustible = (t.get("fuelType") or "").lower()
    imagenes = l.get("images") or []
    grupo = v.get("modelGroup") or v.get("model") or "?"
    return {
        "id": l["id"],
        "pais": pais,
        "url": DOMINIOS[pais] + l.get("url", ""),
        "marca": v.get("make") or "?",
        "grupo": grupo,
        "modelo": v.get("model") or "",
        "version": v.get("modelVersionInput") or v.get("motorTypeName") or "",
        "titulo": f'{v.get("make", "")} {v.get("modelVersionInput") or v.get("model", "")}'.strip(),
        "precio": int(precio),
        "km": km,
        "matriculacion": date(int(m.group(2)), int(m.group(1)), 15).isoformat(),
        "kw": kw,
        "combustible": v.get("fuel") or "",
        "electrico": combustible == "e",
        "cambio": v.get("transmission") or "",
        "ciudad": loc.get("city") or "",
        "cp": loc.get("zip") or "",
        "vendedor": vendedor.get("companyName") or "",
        "etiqueta_as24": t.get("priceLabel") or "",
        "imagen": imagenes[0] if imagenes else "",
    }
