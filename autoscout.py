"""AutoScout24 (España y Alemania): listados y fichas de detalle.

Lee el JSON que la web incrusta en cada página (__NEXT_DATA__).
"""
import json
import re
import urllib.parse
from datetime import date

from comun import Cliente, anuncio, entero

NOMBRE = "AutoScout24"
DOMINIOS = {"ES": "https://www.autoscout24.es", "DE": "https://www.autoscout24.de"}
CODIGO_PAIS = {"ES": "E", "DE": "D"}
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


class AutoScout24:
    def __init__(self):
        self.cliente = Cliente(pausa=(1.5, 3.5))

    def _datos(self, url, pais):
        html = self.cliente.get(url, pais)
        m = _NEXT.search(html or "")
        return json.loads(m.group(1))["props"]["pageProps"] if m else None

    def buscar(self, pais, marca, busq, pagina, solo_hoy):
        params = {
            "atype": "C", "custtype": "D", "cy": CODIGO_PAIS[pais],
            "offer": "U,J,D", "ustate": "N,U", "sort": "age", "desc": "1", "page": str(pagina),
            "fregfrom": str(busq["anio_desde"]), "kmto": str(busq["km_max"]),
            "pricefrom": str(busq["precio_min"]), "priceto": str(busq["precio_max"]),
        }
        if solo_hoy:
            params["adage"] = "1"  # publicados en el último día
        params.update({k: str(v) for k, v in busq.get("extra", {}).items()})
        url = f"{DOMINIOS[pais]}/lst/{marca['slug']}?{urllib.parse.urlencode(params)}"
        pp = self._datos(url, pais)
        if not pp:
            return [], 0
        lista = [a for a in (_anuncio(l, pais, marca) for l in pp.get("listings", [])) if a]
        for a in lista:
            a["publicado_hoy"] = solo_hoy  # los de hoy también salen en la búsqueda con adage=1
        return lista, pp.get("numberOfPages") or 0

    def detalle(self, a):
        pp = self._datos(a["url"], a["pais"])
        if not pp:
            return None
        d = pp.get("listingDetails") or {}
        v = d.get("vehicle") or {}
        publico = (d.get("prices") or {}).get("public") or {}
        texto = str(d.get("warranty") or "")
        m = re.search(r"\d+", texto)
        if m:
            meses = int(m.group())
        else:
            meses = 12 if d.get("warrantyExists") else 0
        return {
            "activo": d.get("status", "Active") == "Active",
            "garantia_meses": meses,
            "mediana_portal": publico.get("median"),
            "co2": (v.get("co2emissionInGramPerKmWithFallback") or {}).get("raw") or a["co2"],
            "publicado": d.get("createdTimestampWithOffset"),
            "carroceria": v.get("bodyType"),
        }


def _anuncio(l, pais, marca):
    v = l.get("vehicle") or {}
    t = l.get("tracking") or {}
    precio = (l.get("price") or {}).get("priceRaw") or entero(t.get("price"))
    km = entero(t.get("mileage"))
    m = re.match(r"(\d{1,2})-(\d{4})", t.get("firstRegistration") or "")
    if not precio or km is None or not m:
        return None
    kw = None
    for det in l.get("vehicleDetails") or []:
        if det.get("iconName") == "speedometer":
            mk = re.search(r"(\d+)\s*kW", det.get("data") or "")
            kw = int(mk.group(1)) if mk else None
    co2 = None
    for w in l.get("wltpValues") or []:  # en Alemania el listado suele traer el CO2
        mc = re.search(r"(\d+)\s*g(?:/| )?\s*(?:CO2)?/?km", str(w), re.I)
        if mc and "co" in str(w).lower():
            co2 = int(mc.group(1))
    loc = l.get("location") or {}
    imagenes = l.get("images") or []
    version = v.get("modelVersionInput") or v.get("motorTypeName") or ""
    return anuncio(
        id="as24:" + l["id"], fuente=NOMBRE, pais=pais,
        url=DOMINIOS[pais] + l.get("url", ""),
        marca=marca["nombre"], grupo=v.get("modelGroup") or v.get("model") or "?",
        titulo=f'{marca["nombre"]} {v.get("model") or v.get("modelGroup") or ""}'.strip(), version=version,
        precio=int(precio), km=km,
        matriculacion=date(int(m.group(2)), int(m.group(1)), 15).isoformat(),
        kw=kw, combustible=v.get("fuel") or "", electrico=(t.get("fuelType") or "").lower() == "e",
        cambio=v.get("transmission") or "", ciudad=loc.get("city") or "",
        vendedor=(l.get("seller") or {}).get("companyName") or "",
        imagen=imagenes[0] if imagenes else "", etiqueta=t.get("priceLabel") or "", co2=co2,
    )
