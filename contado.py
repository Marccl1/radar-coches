"""Precio al contado de AutoScout24 España.

Muchos concesionarios españoles anuncian el precio *financiado* (más bajo) y
ponen el de contado solo en la descripción de la ficha. Como no se pueden abrir
todas las fichas, se aprende la relación contado/anunciado:

  * por concesionario (cada uno suele hacerlo siempre igual), y
  * en general (para concesionarios aún no vistos),

con las fichas que se abren cada día (candidatos + una pequeña muestra al azar),
y se guarda entre ejecuciones en data/contado.json.
"""
import json
import random
from statistics import median

MAX_GENERAL = 300
MAX_VENDEDOR = 10


class Contado:
    def __init__(self, ruta):
        self.ruta = ruta
        datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        self.general = datos.get("general", [])
        self.vendedores = datos.get("vendedores", {})

    def aprender(self, vendedor, anunciado, contado):
        if not (anunciado and contado):
            return
        r = round(contado / anunciado, 4)
        self.general = (self.general + [r])[-MAX_GENERAL:]
        if vendedor:
            self.vendedores[vendedor] = (self.vendedores.get(vendedor, []) + [r])[-MAX_VENDEDOR:]

    def factor(self, vendedor=None):
        if vendedor and self.vendedores.get(vendedor):
            return median(self.vendedores[vendedor])
        return median(self.general) if self.general else 1.0

    def aplicar(self, a):
        """Convierte el precio anunciado de un anuncio de AutoScout24 ES a precio al contado estimado."""
        f = self.factor(a["vendedor"])
        a["precio_anunciado"] = a["precio"]
        if abs(f - 1) > 0.001:
            a["precio"] = round(a["precio"] * f)
            a["contado_estimado"] = True

    def muestra(self, anuncios, n, semilla):
        """Anuncios al azar para medir la relación, priorizando concesionarios aún no vistos."""
        rnd = random.Random(semilla)
        nuevos = [a for a in anuncios if a["vendedor"] not in self.vendedores]
        rnd.shuffle(nuevos)
        resto = [a for a in anuncios if a not in nuevos[:n]]
        rnd.shuffle(resto)
        return (nuevos + resto)[:n]

    def guardar(self):
        self.ruta.parent.mkdir(exist_ok=True)
        self.ruta.write_text(json.dumps({"general": self.general, "vendedores": self.vendedores},
                                        ensure_ascii=False), encoding="utf-8")
