"""Rastreador diario de oportunidades de coches de segunda mano (España + Alemania).

Portales: AutoScout24 (ES, DE), coches.net (ES) y Autohero (ES, DE).

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
from autohero import Autohero
from autoscout import AutoScout24
from cochesnet import CochesNet
from comun import Bloqueado

RAIZ = Path(__file__).parent
HISTORIAL = RAIZ / "data" / "historial.json.gz"
SALIDA = RAIZ / "docs"
DIAS_HISTORIAL = 45
MIN_MUESTRAS_IMPORT = 20  # anuncios comparables en España para fiarse del ahorro de importar


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


# ------------------------------------------------------------------ recogida
def recoger(cfg, rapido, estado):
    busq, port = cfg["busqueda"], cfg["portales"]
    solo_hoy = busq["solo_publicados_hoy"]
    anuncios = []

    def portal(nombre, tarea):
        n0 = len(anuncios)
        try:
            tarea()
            estado[nombre] = f"OK · {len(anuncios) - n0} anuncios"
        except Bloqueado as e:
            estado[nombre] = f"Bloqueado ({e}) · {len(anuncios) - n0} anuncios antes del bloqueo"
            print(f"  ! {nombre} rechaza las peticiones ({e}); se sigue con los demás portales.")
        except Exception as e:  # un portal que cambia su web no debe tumbar el resto
            estado[nombre] = f"Error ({type(e).__name__}) · {len(anuncios) - n0} anuncios antes del error"
            print(f"  ! {nombre} falló: {e!r}; se sigue con los demás portales.")

    def autoscout():
        as24 = portales["AutoScout24"] = AutoScout24()
        planes = [(False, 1 if rapido else port["paginas_mercado"])]  # muestra para valorar el mercado
        if solo_hoy:
            planes.append((True, 2 if rapido else port["paginas_nuevos"]))
        for pais in busq["paises"]:
            for marca in cfg["marcas"]:
                for hoy, paginas in planes:
                    for pagina in range(1, paginas + 1):
                        lista, n_pag = as24.buscar(pais, marca, busq, pagina, hoy)
                        anuncios.extend(lista)
                        if not lista or pagina >= n_pag:
                            break
                print(f"  AutoScout24 {pais} {marca['nombre']:<14} {len(anuncios):>5} acumulados", flush=True)

    def cochesnet():
        cn = portales["coches.net"] = CochesNet()
        for marca in cfg["marcas"]:
            for pagina in range(1, (1 if rapido else port["paginas_cochesnet"]) + 1):
                lista, n_pag = cn.buscar(marca, busq, pagina)
                anuncios.extend(lista)
                if not lista or pagina >= n_pag:
                    break
            print(f"  coches.net  ES {marca['nombre']:<14} {len(anuncios):>5} acumulados", flush=True)

    def autohero():
        ah = Autohero()
        for pais in busq["paises"]:
            for marca in cfg["marcas"]:
                anuncios.extend(ah.buscar(pais, marca, busq))
            print(f"  Autohero    {pais} {'':<14} {len(anuncios):>5} acumulados", flush=True)

    portales = {}
    if port.get("autoscout24"):
        portal("AutoScout24", autoscout)
    if port.get("cochesnet") and "ES" in busq["paises"]:
        portal("coches.net", cochesnet)
    if port.get("autohero"):
        portal("Autohero", autohero)
    return anuncios, portales


def deduplicar(anuncios):
    """Mismo id -> uno. Mismo coche en varios portales (marca, modelo, precio, km) -> uno, con enlaces."""
    por_id = {}
    for a in anuncios:
        previo = por_id.get(a["id"])
        if previo:
            previo["publicado_hoy"] = previo["publicado_hoy"] or a["publicado_hoy"]
        else:
            por_id[a["id"]] = a
    unicos, huellas = [], {}
    for a in por_id.values():
        huella = (a["marca"], a["modelo_norm"], a["precio"], round(a["km"], -2))
        a["tambien_en"] = []
        otro = huellas.get(huella)
        if otro and otro["fuente"] != a["fuente"]:
            otro["tambien_en"].append({"fuente": a["fuente"], "url": a["url"]})
            otro["publicado_hoy"] = otro["publicado_hoy"] or a["publicado_hoy"]
            continue
        huellas[huella] = a
        unicos.append(a)
    return unicos


# ------------------------------------------------------------------ análisis
def valorar(a, mercado, imp):
    esperado = mercado.esperado(a)
    a["esperado"] = round(esperado) if esperado else None
    a["desc_modelo"] = 1 - a["precio"] / esperado if esperado else None
    a["desc_portal"] = 1 - a["precio"] / a["mediana_portal"] if a["mediana_portal"] else None
    descuentos = [d for d in (a["desc_modelo"], a["desc_portal"]) if d is not None]
    a["descuento"] = sum(descuentos) / len(descuentos) if descuentos else None
    a["esperado_es"], a["ahorro_import"], a["importacion"] = None, None, None
    if a["pais"] == "DE" and mercado.muestras(a, "ES") >= MIN_MUESTRAS_IMPORT:
        esp_es = mercado.esperado(a, "ES")
        if esp_es:
            a["importacion"] = analisis.coste_importacion(a, a["co2"], imp)
            a["esperado_es"] = round(esp_es)
            a["ahorro_import"] = 1 - a["importacion"]["total"] / esp_es
    return max([x for x in (a["descuento"], a["ahorro_import"]) if x is not None], default=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads((RAIZ / "config.toml").read_text(encoding="utf-8"))
    busq, op, imp = cfg["busqueda"], cfg["oportunidad"], cfg["importacion"]
    min_marca = {m["nombre"]: m.get("descuento_minimo", op["descuento_minimo"]) for m in cfg["marcas"]}
    ahora = datetime.now(timezone.utc)
    hoy = ahora.date()
    corte = ahora - timedelta(hours=busq["ventana_horas"])
    excluidos = [v.lower() for v in op.get("vendedores_excluidos", [])]

    def excluido(a):
        return any(v in (a["vendedor"] or "").lower() for v in excluidos)

    def iedmt_ok(a):
        """Alemania: solo coches con 0 % de impuesto de matriculación en España (CO2 ≤ 120 g/km o eléctrico)."""
        if a["pais"] != "DE" or not imp.get("solo_iedmt_cero"):
            return True
        return a["electrico"] or (a["co2"] is not None and analisis.tipo_iedmt(a["co2"], False, 1) == 0)

    print("1/4 Leyendo portales...", flush=True)
    estado = {}
    anuncios, portales = recoger(cfg, args.rapido, estado)
    anuncios = deduplicar(anuncios)
    if not anuncios:
        print("No se ha leído ningún anuncio. Se aborta sin tocar el informe.")
        sys.exit(1)

    de = [a for a in anuncios if a["pais"] == "DE"]
    print(f"2/4 Valorando {len(anuncios)} anuncios (CO2 conocido en {sum(a['co2'] is not None for a in de)} "
          f"de {len(de)} alemanes)...", flush=True)
    mercado = analisis.Mercado(anuncios, hoy)
    hist = cargar_historial()
    autohero_conocido = any(k.startswith("ah:") for k in hist)
    candidatos = []
    for a in anuncios:
        h = hist.get(a["id"])
        a["nuevo"] = h is None
        a["primera_vez"] = h["desde"] if h else hoy.isoformat()
        a["precio_inicial"] = h["p0"] if h else a["precio"] + a["bajada_portal"]
        a["bajada"] = max(0, a["precio_inicial"] - a["precio"])
        hist[a["id"]] = {"desde": a["primera_vez"], "p0": a["precio_inicial"], "visto": hoy.isoformat()}

        # ¿publicado en la ventana de hoy?
        if a["publicado"]:
            a["publicado_hoy"] = datetime.fromisoformat(a["publicado"].replace("Z", "+00:00")) >= corte
        elif a["publicado_hoy"] is None:
            a["publicado_hoy"] = a["nuevo"] and (a["fuente"] != "Autohero" or autohero_conocido)

        mejor = valorar(a, mercado, imp)
        if busq["solo_publicados_hoy"] and not a["publicado_hoy"]:
            continue
        if a["garantia_meses"] is not None and a["garantia_meses"] < op["garantia_meses_minima"]:
            continue
        if excluido(a) or (a["co2"] is not None and not iedmt_ok(a)):  # el CO2 puede llegar con la ficha
            continue
        umbral = min_marca.get(a["marca"], op["descuento_minimo"])
        if (mejor is not None and mejor >= umbral - 0.04) or a["etiqueta"] == "top-price":
            a["_prefiltro"] = mejor if mejor is not None else 0
            candidatos.append(a)

    candidatos.sort(key=lambda a: -a["_prefiltro"])
    # Fichas a abrir por portal: (cliente, máximo al día)
    fichas = {"AutoScout24": [portales.get("AutoScout24"), 15 if args.rapido else op["max_fichas"]],
              "coches.net": [portales.get("coches.net"), 5 if args.rapido else op["max_fichas_cochesnet"]]}
    print(f"3/4 {len(candidatos)} candidatos; verificando fichas (garantía, vendedor, CO2)...", flush=True)
    oportunidades = []
    for a in candidatos:
        if a["fuente"] in fichas:
            cliente, restantes = fichas[a["fuente"]]
            if not cliente or restantes <= 0:
                continue
            fichas[a["fuente"]][1] -= 1
            try:
                d = cliente.detalle(a)
            except Bloqueado:
                print(f"  {a['fuente']} empezó a rechazar fichas; se sigue con lo verificado.")
                fichas[a["fuente"]][0] = None
                continue
            if not d or not d.pop("activo"):
                continue
            a.update(d)
        if excluido(a) or not iedmt_ok(a):
            continue
        if (a["garantia_meses"] or 0) < op["garantia_meses_minima"]:
            continue
        mejor = valorar(a, mercado, imp)
        if mejor is None or mejor < min_marca.get(a["marca"], op["descuento_minimo"]):
            continue
        a["sospechoso"] = mejor > 0.35
        a["puntuacion"] = round(
            100 * mejor
            + min(4, (a["garantia_meses"] - 12) / 6)
            + (3 if a["bajada"] else 0)
            + (1 if len(a["tambien_en"]) else 0)
            - (15 if a["sospechoso"] else 0), 1)
        a.pop("_prefiltro", None)
        oportunidades.append(a)
        print(f"  ✓ {a['fuente']:<11} {a['pais']} {a['titulo'][:38]:<38} {a['precio']:>7} €  "
              f"-{100 * mejor:.0f}%  garantía {a['garantia_meses']}m", flush=True)

    oportunidades.sort(key=lambda a: -a["puntuacion"])
    oportunidades = oportunidades[:op["max_en_informe"]]

    print("4/4 Generando informe...", flush=True)
    n_hist = guardar_historial(hist, hoy)
    resumen = {
        "generado": ahora.isoformat(timespec="minutes"),
        "analizados": len(anuncios),
        "por_pais": {p: sum(a["pais"] == p for a in anuncios) for p in busq["paises"]},
        "publicados_hoy": sum(bool(a["publicado_hoy"]) for a in anuncios),
        "portales": estado,
        "modelos_valorados": len(mercado.modelos),
        "historial": n_hist,
        "config": {k: v for k, v in busq.items() if k != "extra"},
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
    for nombre, txt in estado.items():
        print(f"  {nombre}: {txt}")


if __name__ == "__main__":
    main()
