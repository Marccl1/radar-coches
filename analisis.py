"""Valoración de mercado: modelo de precio por modelo y país, y coste de importar.

Para cada (país, marca, modelo, eléctrico/no) se ajusta
    ln(precio) = b0 + b1·antigüedad + b2·ln(km + 10.000) + b3·ln(kW)
con los anuncios del día. El precio esperado de un coche sale de ese modelo,
y el descuento es lo que el anuncio está por debajo.
"""
import math
from collections import defaultdict
from datetime import date

MIN_MUESTRAS = 10


def clave(a):
    return (a["marca"], a["modelo_norm"], a["electrico"])


def antiguedad(a, hoy):
    return max(0.0, (hoy - date.fromisoformat(a["matriculacion"])).days / 365.25)


def _rasgos(a, kw_tipico, hoy):
    return [1.0, antiguedad(a, hoy), math.log(a["km"] + 10000), math.log(a["kw"] or kw_tipico)]


def _resolver(A, b):
    """Eliminación gaussiana con pivoteo parcial."""
    n = len(b)
    M = [fila[:] + [b[i]] for i, fila in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            return None
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))) / M[r][r]
    return x


def _mco(X, y, ridge=0.05):
    n = len(X[0])
    A = [[sum(x[i] * x[j] for x in X) + (ridge if i == j and i > 0 else 0.0) for j in range(n)]
         for i in range(n)]
    b = [sum(x[i] * yi for x, yi in zip(X, y)) for i in range(n)]
    return _resolver(A, b)


def _predecir(beta, rasgos):
    return sum(b * r for b, r in zip(beta, rasgos))


class Mercado:
    def __init__(self, anuncios, hoy):
        self.hoy = hoy
        self.anuncios = anuncios
        self.modelos = {}
        grupos = defaultdict(list)
        for a in anuncios:
            grupos[(a["pais"],) + clave(a)].append(a)
        for g, lista in grupos.items():
            if len(lista) < MIN_MUESTRAS:
                continue
            kws = sorted(a["kw"] for a in lista if a["kw"])
            kw_tipico = kws[len(kws) // 2] if kws else 100
            beta, sigma = None, None
            usados = lista
            for _ in range(2):  # segundo ajuste sin valores atípicos
                X = [_rasgos(a, kw_tipico, hoy) for a in usados]
                y = [math.log(a["precio"]) for a in usados]
                beta = _mco(X, y)
                if not beta:
                    break
                res = [yi - _predecir(beta, x) for x, yi in zip(X, y)]
                sigma = math.sqrt(sum(r * r for r in res) / max(1, len(res) - 4))
                filtrados = [a for a, r in zip(usados, res) if abs(r) <= 2.5 * sigma]
                if len(filtrados) < MIN_MUESTRAS or len(filtrados) == len(usados):
                    break
                usados = filtrados
            if beta:
                self.modelos[g] = {"beta": beta, "kw": kw_tipico, "sigma": sigma, "n": len(lista)}

    def esperado(self, a, pais=None):
        """Precio esperado del coche `a` en el mercado `pais` (por defecto, el suyo)."""
        m = self.modelos.get(((pais or a["pais"]),) + clave(a))
        if not m:
            return None
        return math.exp(_predecir(m["beta"], _rasgos(a, m["kw"], self.hoy)))

    def muestras(self, a, pais=None):
        m = self.modelos.get(((pais or a["pais"]),) + clave(a))
        return m["n"] if m else 0

    def comparativa_paises(self, referencia_edad=4, referencia_km=60000):
        """Precio típico de cada modelo (4 años, 60.000 km) en ES y DE."""
        filas = []
        nombres = {clave(a): a["grupo"] for a in self.anuncios}
        claves = {g[1:] for g in self.modelos}
        for c in claves:
            es, de = self.modelos.get(("ES",) + c), self.modelos.get(("DE",) + c)
            if not (es and de):
                continue
            kw = es["kw"]
            r = [1.0, referencia_edad, math.log(referencia_km + 10000), math.log(kw)]
            p_es, p_de = math.exp(_predecir(es["beta"], r)), math.exp(_predecir(de["beta"], r))
            if not (1000 < p_es < 500000 and 1000 < p_de < 500000):
                continue
            filas.append({
                "modelo": f"{c[0]} {nombres.get(c, c[1])}" + (" (eléctrico)" if c[2] else ""),
                "precio_es": round(p_es, -2), "precio_de": round(p_de, -2),
                "diferencia": (p_es - p_de) / p_es,
                "n_es": es["n"], "n_de": de["n"],
            })
        return sorted(filas, key=lambda f: -f["diferencia"])


def tipo_iedmt(co2, electrico, por_defecto):
    """Impuesto especial de matriculación (península), por g/km de CO2 WLTP."""
    if electrico:
        return 0.0
    if co2 is None:
        return por_defecto
    if co2 <= 120:
        return 0.0
    if co2 < 160:
        return 0.0475
    if co2 < 200:
        return 0.0975
    return 0.1475


def coste_importacion(a, co2, cfg):
    """Precio alemán + transporte + gestión + IEDMT (base aproximada: precio de compra)."""
    tipo = tipo_iedmt(co2, a["electrico"], cfg["tipo_iedmt_sin_co2"])
    impuesto = a["precio"] * tipo
    total = a["precio"] + cfg["transporte"] + cfg["gestion_itv_placas"] + impuesto
    return {"total": round(total), "iedmt": round(impuesto), "tipo_iedmt": tipo,
            "co2_estimado": co2 is None}
