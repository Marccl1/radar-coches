"""Genera el informe HTML (autocontenido) a partir de los datos del día."""
import json

PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar de chollos</title>
<style>
:root{
  --bg:#f6f4ef;--panel:#ffffff;--ink:#1d1c1a;--muted:#6b6862;--line:#e4e0d6;
  --accent:#1f6f50;--accent-soft:#e2f1ea;--warn:#a5520f;--warn-soft:#fbeedd;
  --bad:#a12a2a;--bad-soft:#f8e3e1;--chip:#efece4;--shadow:0 1px 2px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.04);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#141413;--panel:#1e1d1b;--ink:#efece6;--muted:#a19d95;--line:#33312d;
  --accent:#5fc49a;--accent-soft:#1d3a2e;--warn:#f0a35e;--warn-soft:#3a2a1a;
  --bad:#f08a80;--bad-soft:#3d1f1d;--chip:#2a2926;--shadow:none;}}
:root[data-theme="dark"]{
  --bg:#141413;--panel:#1e1d1b;--ink:#efece6;--muted:#a19d95;--line:#33312d;
  --accent:#5fc49a;--accent-soft:#1d3a2e;--warn:#f0a35e;--warn-soft:#3a2a1a;
  --bad:#f08a80;--bad-soft:#3d1f1d;--chip:#2a2926;--shadow:none;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 16px 60px}
header h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}
header p{margin:0;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:22px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.stat span{color:var(--muted);font-size:13px}
.filtros{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0 18px}
.filtros select,.filtros button,.filtros label{font:inherit;font-size:14px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}
.filtros button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.filtros .cuenta{color:var(--muted);margin-left:auto;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column}
.foto{position:relative;aspect-ratio:4/3;background:var(--chip)}
.foto img{width:100%;height:100%;object-fit:cover;display:block}
.badges{position:absolute;top:10px;left:10px;display:flex;gap:6px;flex-wrap:wrap}
.badge{font-size:12px;font-weight:600;padding:3px 8px;border-radius:999px;background:var(--panel);color:var(--ink)}
.badge.ok{background:var(--accent);color:#fff}.badge.warn{background:var(--warn);color:#fff}.badge.bad{background:var(--bad);color:#fff}
.desc{position:absolute;right:10px;bottom:10px;background:var(--accent);color:#fff;font-weight:700;padding:5px 10px;border-radius:10px;font-size:16px}
.body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:10px;flex:1}
.titulo{font-weight:650;font-size:16px;line-height:1.3}
.sub{color:var(--muted);font-size:13px}
.precio{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.precio b{font-size:24px;font-variant-numeric:tabular-nums}
.precio s{color:var(--muted)}
.specs{display:flex;flex-wrap:wrap;gap:6px}
.specs span{background:var(--chip);border-radius:6px;padding:2px 8px;font-size:13px}
.import{background:var(--accent-soft);border-radius:10px;padding:10px 12px;font-size:13px}
.import.neg{background:var(--warn-soft)}
.import b{font-variant-numeric:tabular-nums}
.pie{margin-top:auto;display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
.pie a{background:var(--ink);color:var(--bg);text-decoration:none;padding:7px 12px;border-radius:8px;font-weight:600;white-space:nowrap}
h2{margin:44px 0 6px;font-size:20px}
.nota{color:var(--muted);font-size:14px;margin:0 0 14px}
.tabla{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap;font-variant-numeric:tabular-nums}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}
.pos{color:var(--accent);font-weight:600}.neg{color:var(--bad)}
.vacio{padding:40px;text-align:center;color:var(--muted);background:var(--panel);border:1px dashed var(--line);border-radius:14px}
footer{margin-top:44px;color:var(--muted);font-size:13px}
footer li{margin:4px 0}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Radar de chollos</h1>
    <p id="fecha"></p>
  </header>
  <section class="stats" id="stats"></section>
  <div class="filtros" id="filtros">
    <button data-pais="" aria-pressed="true">Todos</button>
    <button data-pais="ES" aria-pressed="false">España</button>
    <button data-pais="DE" aria-pressed="false">Alemania</button>
    <select id="marca" aria-label="Marca"><option value="">Todas las marcas</option></select>
    <select id="orden" aria-label="Orden">
      <option value="puntuacion">Mejor oportunidad</option>
      <option value="descuento">Mayor descuento</option>
      <option value="precio">Precio más bajo</option>
      <option value="km">Menos km</option>
      <option value="garantia">Más garantía</option>
    </select>
    <label><input type="checkbox" id="bajadas"> Solo con bajada de precio</label>
    <span class="cuenta" id="cuenta"></span>
  </div>
  <section class="grid" id="grid"></section>

  <h2>España vs Alemania</h2>
  <p class="nota">Precio típico de cada modelo con 4 años y 60.000 km, según los anuncios de hoy. Positivo = más barato en Alemania (antes de transporte e impuestos).</p>
  <div class="tabla"><table id="comparativa"></table></div>

  <footer>
    <p><b>Cómo se calcula</b></p>
    <ul>
      <li>Solo vendedores profesionales con garantía verificada en la ficha del anuncio.</li>
      <li>Descuento = media entre el precio esperado por nuestro modelo (antigüedad, km y potencia de ese modelo en ese país) y la mediana de mercado de AutoScout24.</li>
      <li>Coches alemanes: “puesto en España” suma transporte, ITV/gestoría/placas e impuesto de matriculación según CO2 (base aproximada: precio de compra). Es una estimación: pide presupuesto antes de comprar.</li>
      <li>“Revisar” marca precios demasiado bajos (&gt;35 % por debajo): pueden ser errores, daños no declarados o fraude.</li>
    </ul>
  </footer>
</div>
<script id="datos" type="application/json">__DATOS__</script>
<script>
const D = JSON.parse(document.getElementById('datos').textContent);
const R = D.resumen;
const eur = n => n == null ? '–' : new Intl.NumberFormat('es-ES',{maximumFractionDigits:0}).format(n) + ' €';
const num = n => new Intl.NumberFormat('es-ES').format(n);
const pct = x => x == null ? '–' : Math.round(x*100) + ' %';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const PAIS = {ES:'España', DE:'Alemania'};
const mejor = o => Math.max(o.descuento ?? -1, o.ahorro_import ?? -1);

document.getElementById('fecha').textContent =
  'Actualizado ' + new Date(R.generado).toLocaleString('es-ES',{dateStyle:'full',timeStyle:'short'}) +
  ' · desde ' + R.config.anio_desde + ', hasta ' + num(R.config.km_max) + ' km, ' + eur(R.config.precio_min) + '–' + eur(R.config.precio_max);

const stats = [
  [D.oportunidades.length, 'oportunidades'],
  [num(R.analizados), 'anuncios analizados'],
  [Object.entries(R.por_pais).map(([p,n]) => p + ' ' + num(n)).join(' · '), 'por país'],
  [num(R.nuevos), 'anuncios nuevos hoy'],
  [R.modelos_valorados, 'modelos con valoración'],
];
document.getElementById('stats').innerHTML = stats.map(([v,t]) => `<div class="stat"><b>${v}</b><span>${t}</span></div>`).join('');

const marcas = [...new Set(D.oportunidades.map(o => o.marca))].sort();
document.getElementById('marca').innerHTML += marcas.map(m => `<option>${esc(m)}</option>`).join('');

let pais = '';
function tarjeta(o){
  const b = [];
  b.push(`<span class="badge">${o.pais}</span>`);
  if (o.nuevo) b.push('<span class="badge ok">Nuevo hoy</span>');
  if (o.bajada) b.push(`<span class="badge warn">Bajó ${eur(o.bajada)}</span>`);
  if (o.sospechoso) b.push('<span class="badge bad">Revisar</span>');
  const anio = o.matriculacion.slice(0,4);
  const cv = o.kw ? Math.round(o.kw*1.36) + ' CV' : null;
  const specs = [anio, num(o.km)+' km', cv, o.combustible, o.cambio].filter(Boolean).map(s => `<span>${esc(s)}</span>`).join('');
  let imp = '';
  if (o.pais === 'DE' && o.importacion && o.esperado_es){
    const ahorro = o.esperado_es - o.importacion.total;
    imp = `<div class="import ${ahorro < 0 ? 'neg' : ''}">Puesto en España: <b>${eur(o.importacion.total)}</b>
      (IEDMT ${Math.round(o.importacion.tipo_iedmt*1000)/10} %${o.importacion.co2_estimado ? ' estimado' : ''})<br>
      En España costaría ~<b>${eur(o.esperado_es)}</b> → ${ahorro >= 0 ? 'ahorras' : 'pierdes'} <b>${eur(Math.abs(ahorro))}</b></div>`;
  }
  const ref = o.mediana_as24 || o.esperado;
  return `<article class="card">
    <div class="foto">${o.imagen ? `<img loading="lazy" src="${esc(o.imagen)}" alt="">` : ''}
      <div class="badges">${b.join('')}</div>
      ${o.descuento != null ? `<div class="desc">−${Math.round(o.descuento*100)} %</div>` : ''}</div>
    <div class="body">
      <div><div class="titulo">${esc(o.titulo)}</div><div class="sub">${esc(o.grupo)} · ${esc(o.carroceria || '')}</div></div>
      <div class="precio"><b>${eur(o.precio)}</b>${ref ? `<s>${eur(ref)}</s><span class="sub">mercado</span>` : ''}</div>
      <div class="specs">${specs}</div>
      ${imp}
      <div class="sub">Garantía <b>${o.garantia_meses} meses</b> · en venta desde ${new Date(o.primera_vez).toLocaleDateString('es-ES')}</div>
      <div class="pie"><span>${esc(o.vendedor)}<br>${esc(o.ciudad)} (${PAIS[o.pais]})</span>
        <a href="${esc(o.url)}" target="_blank" rel="noopener">Ver anuncio</a></div>
    </div></article>`;
}

function pintar(){
  const marca = document.getElementById('marca').value;
  const orden = document.getElementById('orden').value;
  const soloBajadas = document.getElementById('bajadas').checked;
  let l = D.oportunidades.filter(o => (!pais || o.pais === pais) && (!marca || o.marca === marca) && (!soloBajadas || o.bajada));
  const k = {puntuacion: o => -o.puntuacion, descuento: o => -mejor(o), precio: o => o.precio, km: o => o.km, garantia: o => -o.garantia_meses}[orden];
  l.sort((a,b) => k(a) - k(b));
  document.getElementById('cuenta').textContent = l.length + ' resultados';
  document.getElementById('grid').innerHTML = l.length ? l.map(tarjeta).join('')
    : '<div class="vacio">No hay oportunidades con estos filtros hoy.</div>';
}
document.querySelectorAll('[data-pais]').forEach(btn => btn.addEventListener('click', () => {
  pais = btn.dataset.pais;
  document.querySelectorAll('[data-pais]').forEach(x => x.setAttribute('aria-pressed', x === btn));
  pintar();
}));
['marca','orden','bajadas'].forEach(id => document.getElementById(id).addEventListener('change', pintar));
pintar();

const C = D.comparativa;
document.getElementById('comparativa').innerHTML = C.length
  ? '<tr><th>Modelo</th><th>España</th><th>Alemania</th><th>Diferencia</th><th>Muestras</th></tr>' +
    C.map(c => `<tr><td>${esc(c.modelo)}</td><td>${eur(c.precio_es)}</td><td>${eur(c.precio_de)}</td>
      <td class="${c.diferencia >= 0 ? 'pos' : 'neg'}">${c.diferencia >= 0 ? '+' : ''}${pct(c.diferencia)}</td>
      <td>${c.n_es} / ${c.n_de}</td></tr>`).join('')
  : '<tr><td>Aún no hay suficientes anuncios en ambos países.</td></tr>';
</script>
</body>
</html>
"""


def html(datos):
    js = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    return PLANTILLA.replace("__DATOS__", js)
