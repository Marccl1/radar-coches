"""Rastreador diario de oportunidades de coches de segunda mano (España + Alemania).

Uso:
    python rastreador.py            # rastreo completo
    python rastreador.py --rapido   # 1 página por búsqueda y pocas fichas (para probar)
"""
import argparse
import gzip
import json
import sys
import tomllib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import analisis
import informe
from autoscout import Bloqueado, Cliente

RAIZ = Path(__file__).parent
HISTORIAL = RAIZ / "data" / "historial.json.gz"
SALIDA = RAIZ / "docs"
DIAS_HISTORIAL = 45


def cargar_historial():
    if HISTORIAL.exists():
        with gzip.open(HISTORIAL, "rt", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_historial(hist, hoy):
    limite = (hoy - timedelta(days=DIAS_HISTORIAL)).isoformat()
    hist = {k: v for k, v in hist.items() if v["visto"] >= limite}
    HISTORIAL.parent.mkdir(exist_ok=True)
    with gzip.open(HISTORIAL, "wt", encoding="utf-8") as f:
        json.dump(hist, f, separators=(",", ":"))
    return len(hist)


def recoger(cliente, cfg, rapido):
    busq = cfg["busqueda"]
    paginas = 1 if rapido else busq["paginas_por_busqueda"]
    vistos = {}
    for pais in busq["paises"]:
        for marca in cfg["marcas"]:
            total = 0
            for pagina in range(1, paginas + 1):
                anuncios, n_paginas = cliente.buscar(pais, marca["slug"], busq, pagina)
                for a in anuncios:
                    a["marca_cfg"] = marca["slug"]
                    vistos[a["id"]] = a
                total += len(anuncios)
                if not anuncios or pagina >= n_paginas:
                    break
            print(f"  {pais} {marca['nombre']:<14} {total:>4} anuncios", flush=True)
    return list(vistos.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads((RAIZ / "config.toml").read_text(encoding="utf-8"))
    op, imp = cfg["oportunidad"], cfg["importacion"]
    min_marca = {m["slug"]: m.get("descuento_minimo", op["descuento_minimo"]) for m in cfg["marcas"]}
    hoy = date.today()
    cliente = Cliente()

    print("1/4 Leyendo anuncios...", flush=True)
    try:
        anuncios = recoger(cliente, cfg, args.rapido)
    except Bloqueado as e:
        print(f"AutoScout24 está rechazando las peticiones ({e}). Se aborta sin tocar el informe.")
        sys.exit(2)
    if not anuncios:
        print("No se ha leído ningún anuncio. Se aborta sin tocar el informe.")
        sys.exit(1)

    print(f"2/4 Valorando {len(anuncios)} anuncios...", flush=True)
    mercado = analisis.Mercado(anuncios, hoy)
    hist = cargar_historial()
    candidatos = []
    for a in anuncios:
        h = hist.get(a["id"])
        a["nuevo"] = h is None
        a["primera_vez"] = h["desde"] if h else hoy.isoformat()
        a["precio_inicial"] = h["p0"] if h else a["precio"]
        a["bajada"] = max(0, a["precio_inicial"] - a["precio"])
        hist[a["id"]] = {"desde": a["primera_vez"], "p0": a["precio_inicial"],
                         "visto": hoy.isoformat()}

        esperado = mercado.esperado(a)
        a["esperado"] = round(esperado) if esperado else None
        a["desc_modelo"] = 1 - a["precio"] / esperado if esperado else None
        a["esperado_es"] = None
        a["ahorro_import"] = None
        if a["pais"] == "DE":
            esp_es = mercado.esperado(a, "ES")
            if esp_es:
                coste = analisis.coste_importacion(a, None, imp)
                a["esperado_es"] = round(esp_es)
                a["ahorro_import"] = 1 - coste["total"] / esp_es
        mejor = max(x for x in (a["desc_modelo"], a["ahorro_import"], -1) if x is not None)
        umbral = min_marca.get(a["marca_cfg"], op["descuento_minimo"])
        if mejor >= umbral - 0.04 or a["etiqueta_as24"] == "top-price":
            a["_prefiltro"] = mejor
            candidatos.append(a)

    candidatos.sort(key=lambda a: -a["_prefiltro"])
    max_fichas = 15 if args.rapido else op["max_fichas"]
    print(f"3/4 Verificando garantía y mercado de {min(len(candidatos), max_fichas)} "
          f"de {len(candidatos)} candidatos...", flush=True)

    oportunidades = []
    for a in candidatos[:max_fichas]:
        try:
            d = cliente.detalle(a)
        except Bloqueado:
            print("  AutoScout24 empezó a rechazar fichas; se sigue con lo verificado.")
            break
        if not d or not d["activo"] or d["garantia_meses"] < op["garantia_meses_minima"]:
            continue
        a.update(d)
        descuentos = [a["desc_modelo"]] if a["desc_modelo"] is not None else []
        if d["mediana_as24"]:
            a["desc_as24"] = 1 - a["precio"] / d["mediana_as24"]
            descuentos.append(a["desc_as24"])
        else:
            a["desc_as24"] = None
        a["descuento"] = sum(descuentos) / len(descuentos) if descuentos else None
        if a["pais"] == "DE" and a["esperado_es"]:
            coste = analisis.coste_importacion(a, d["co2"], imp)
            a["importacion"] = coste
            a["ahorro_import"] = 1 - coste["total"] / a["esperado_es"]
        mejor = max(x for x in (a["descuento"], a["ahorro_import"], -1) if x is not None)
        if mejor < min_marca.get(a["marca_cfg"], op["descuento_minimo"]):
            continue
        a["sospechoso"] = (a["descuento"] or 0) > 0.35
        a["puntuacion"] = round(
            100 * mejor
            + min(4, (a["garantia_meses"] - 12) / 6)
            + (3 if a["bajada"] else 0)
            + (1 if a["nuevo"] else 0)
            - (15 if a["sospechoso"] else 0), 1)
        a.pop("_prefiltro", None)
        oportunidades.append(a)
        print(f"  ✓ {a['pais']} {a['titulo'][:40]:<40} {a['precio']:>7} €  "
              f"-{100 * mejor:.0f}%  garantía {a['garantia_meses']}m", flush=True)

    oportunidades.sort(key=lambda a: -a["puntuacion"])
    oportunidades = oportunidades[:op["max_en_informe"]]

    print("4/4 Generando informe...", flush=True)
    n_hist = guardar_historial(hist, hoy)
    resumen = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "analizados": len(anuncios),
        "por_pais": {p: sum(a["pais"] == p for a in anuncios) for p in cfg["busqueda"]["paises"]},
        "nuevos": sum(a["nuevo"] for a in anuncios),
        "peticiones": cliente.peticiones,
        "modelos_valorados": len(mercado.modelos),
        "historial": n_hist,
        "config": {k: v for k, v in cfg["busqueda"].items() if k != "extra"},
        "descuento_minimo": op["descuento_minimo"],
        "garantia_minima": op["garantia_meses_minima"],
        "importacion": imp,
    }
    SALIDA.mkdir(exist_ok=True)
    datos = {"resumen": resumen, "oportunidades": oportunidades,
             "comparativa": mercado.comparativa_paises()[:25]}
    (SALIDA / "oportunidades.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDA / "index.html").write_text(informe.html(datos), encoding="utf-8")
    print(f"Listo: {len(oportunidades)} oportunidades -> {SALIDA / 'index.html'}")


if __name__ == "__main__":
    main()
