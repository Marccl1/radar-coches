"""Autohero (España y Alemania). Vende sus propios coches, todos con 12 meses de garantía.

No publica fecha de anuncio: un coche cuenta como «nuevo» el primer día que el
rastreador lo ve.
"""
import html as H
import re
import urllib.parse

from comun import Cliente, anuncio, entero

NOMBRE = "Autohero"
BASE = "https://www.autohero.com"
_TARJETA = re.compile(
    r'<a href="(/(?:es|de)/[^"]+/id/([0-9a-f-]{36})/)" data-qa-selector="ad-card-link"[^>]*>(.*?)</a>', re.S)
_CONTADO = ("Al contado", "Barpreis", "Barzahlung")


class Autohero:
    def __init__(self):
        self.cliente = Cliente(pausa=(3, 6))

    def buscar(self, pais, marca, busq):
        params = {"brand": marca["slug"], "mileageMax": busq["km_max"]}
        url = f"{BASE}/{pais.lower()}/search/?{urllib.parse.urlencode(params)}"
        html = self.cliente.get(url, pais) or ""
        lista = []
        for m in _TARJETA.finditer(html):
            a = _anuncio(m, pais, marca)
            if a and a["precio"] and busq["precio_min"] <= a["precio"] <= busq["precio_max"] \
                    and a["matriculacion"] >= f"{busq['anio_desde']}-01-01":
                lista.append(a)
        return lista


def _anuncio(m, pais, marca):
    href, ident, tarjeta = m.groups()
    sel = {k: H.unescape(v).strip() for k, v in re.findall(r'data-qa-selector="([^"]+)"[^>]*>([^<]+)<', tarjeta)}
    textos = [H.unescape(t).strip() for t in re.sub(r"<[^>]+>", "|", tarjeta).split("|")]
    textos = [t for t in textos if t and t != "•"]
    precio = entero(sel.get("price"))
    for i, t in enumerate(textos[:-1]):
        if t in _CONTADO:
            precio = entero(textos[i + 1]) or precio
    anio = next((i for i, t in enumerate(textos) if re.fullmatch(r"(19|20)\d\d", t)), None)
    km = next((entero(t) for t in textos if re.fullmatch(r"[\d.]+ km", t)), None)
    if anio is None or km is None:
        return None
    co2 = next((int(x.group(1)) for t in textos if (x := re.match(r"(\d+) g CO2", t))), None)
    titulo = sel.get("title") or marca["nombre"]
    grupo = titulo[len(marca["nombre"]):].strip() if titulo.lower().startswith(marca["nombre"].lower()) \
        else titulo.split(" ", 1)[-1]
    km_idx = next(i for i, t in enumerate(textos) if re.fullmatch(r"[\d.]+ km", t))
    cambio = next((t for t in textos[km_idx + 1:km_idx + 4] if t not in _CONTADO and "€" not in t), "")
    imagen = re.search(r'<img[^>]+src="([^"]+)"', tarjeta)
    return anuncio(
        id=f"ah:{ident}", fuente=NOMBRE, pais=pais, url=BASE + href, marca=marca["nombre"],
        grupo=grupo, titulo=f"{titulo} {sel.get('subtitle', '')}".strip(), version=sel.get("subtitle", ""),
        precio=precio, km=km, matriculacion=f"{textos[anio]}-07-01",
        combustible=textos[anio + 1] if anio + 1 < len(textos) else "",
        cambio=cambio,
        vendedor="Autohero", imagen=imagen.group(1) if imagen else "",
        garantia_meses=12, co2=co2,
    )
