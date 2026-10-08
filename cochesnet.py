"""coches.net (solo España, solo profesionales).

Cada anuncio del listado ya trae garantía, fecha de publicación, bajada de precio
y el precio medio de mercado que calcula coches.net, así que no hace falta abrir
fichas. El portal tiene protección anti-bots: se hacen pocas peticiones, muy
espaciadas, y se para en cuanto aparece su página de bloqueo.
"""
import json
import urllib.parse

from comun import Cliente, anuncio

NOMBRE = "coches.net"
BASE = "https://www.coches.net"
_INICIO = "window.__INITIAL_PROPS__ = JSON.parse("


class CochesNet:
    def __init__(self):
        self.cliente = Cliente(pausa=(12, 25), marcas_bloqueo=("Parece que algo no va bien",))

    def buscar(self, marca, busq, pagina):
        params = {
            "st": "1",  # profesionales
            "MaxKms": busq["km_max"], "MinYear": busq["anio_desde"],
            "MinPrice": busq["precio_min"], "MaxPrice": busq["precio_max"], "pg": pagina,
        }
        html = self.cliente.get(f"{BASE}/{marca['slug']}/segunda-mano/?{urllib.parse.urlencode(params)}")
        if not html or _INICIO not in html:
            return [], 0
        texto, _ = json.JSONDecoder().raw_decode(html, html.index(_INICIO) + len(_INICIO))
        res = json.loads(texto).get("initialResults") or {}
        lista = [a for a in (_anuncio(i, marca) for i in res.get("items", [])) if a]
        return lista, res.get("totalPages") or 0


def _anuncio(i, marca):
    if not i.get("isProfessional") or not i.get("price") or not i.get("year"):
        return None
    loc = i.get("location") or {}
    caida = i.get("priceDrop") or {}
    hp = i.get("hp")
    modelo = i.get("model") or "?"
    titulo = i.get("title") or f"{marca['nombre']} {modelo}"
    return anuncio(
        id=f"cn:{i['id']}", fuente=NOMBRE, pais="ES", url=BASE + (i.get("url") or ""),
        marca=marca["nombre"], grupo=modelo, titulo=titulo,
        version=titulo.split(modelo, 1)[-1].strip() if modelo in titulo else "",
        precio=int(i["price"]), km=int(i.get("km") or 0),
        matriculacion=f"{int(i['year'])}-07-01",
        kw=round(hp / 1.36) if hp else None, combustible=i.get("fuelType") or "",
        ciudad=loc.get("cityLiteral") or loc.get("mainProvince") or "",
        vendedor="Profesional", imagen=i.get("imgUrl") or i.get("img") or "",
        publicado=i.get("publicationDate"),
        garantia_meses=12 if i.get("hasWarranty") else 0,  # 12 = mínimo legal de un profesional
        mediana_portal=i.get("priceAverageIndicator") or None,
        bajada_portal=max(0, (caida.get("originalPrice") or 0) - int(i["price"])),
    )
