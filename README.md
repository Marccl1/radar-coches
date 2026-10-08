# Radar de chollos — coches de segunda mano ES + DE

Cada mañana rastrea AutoScout24 España y Alemania (Audi, BMW, Mercedes-Benz,
Volkswagen, Toyota y Mazda), se queda con lo que está claramente por debajo de
mercado, comprueba que el vendedor es profesional y da garantía, y publica un
informe web con fotos, descuento, coste puesto en España y bajadas de precio.

## Cómo decide qué es una oportunidad

1. **Lee los anuncios más recientes** de cada marca en cada país (solo profesionales).
2. **Valora el mercado**: para cada modelo y país ajusta un modelo de precio
   (antigüedad, km y potencia) con los anuncios del día.
3. **Preselecciona** los que están por debajo de lo esperado.
4. **Abre la ficha** de cada candidato: verifica garantía (≥ 12 meses), coge la
   mediana de mercado de AutoScout24 y el CO2.
5. **Descuento final** = media entre nuestro modelo y la mediana de AutoScout24.
   Para coches alemanes calcula además el **coste puesto en España**
   (transporte + ITV/gestoría/placas + impuesto de matriculación según CO2) y lo
   compara con el precio típico en España.
6. Puntúa: descuento, meses de garantía extra, bajadas de precio y anuncio nuevo.
   Si algo está > 35 % por debajo lo marca como **Revisar** (posible error o fraude).

Todo se ajusta en [`config.toml`](config.toml): años, km, precios, marcas,
descuento mínimo, garantía mínima y costes de importación.

## Ponerlo en marcha en la nube (GitHub, gratis)

1. Crea una cuenta en <https://github.com> si no tienes.
2. Crea un repositorio nuevo **público** (p. ej. `radar-coches`). GitHub Pages
   gratis requiere repo público; solo contiene el código y tus filtros.
3. En el repositorio: **Add file → Upload files** y arrastra el contenido de esta
   carpeta, **incluida la carpeta `.github`** (en Windows, si no la ves, activa
   "Elementos ocultos" en el Explorador). Commit.
4. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. **Actions → Rastreo diario → Run workflow** para la primera ejecución
   (tarda ~10-15 min).
6. Tu informe queda en `https://<tu-usuario>.github.io/radar-coches/`.
   Guárdalo en favoritos del móvil. Se actualiza solo cada día a las 07:30.

## Ejecutarlo en tu PC

```
python rastreador.py            # completo (~10-15 min)
python rastreador.py --rapido   # prueba rápida
```

Abre `docs/index.html`. Solo necesita Python 3.11+ (sin librerías extra).

## Avisos

- Los números de importación son **estimaciones**: el impuesto de matriculación
  real se calcula sobre las tablas de Hacienda, no sobre el precio de compra.
  Pide presupuesto de transporte y gestoría antes de comprar.
- Las condiciones de uso de AutoScout24 restringen el acceso automatizado. El
  rastreador hace pocas peticiones, con pausas, para uso personal, y se detiene
  si el sitio empieza a rechazarlas. Si un día deja de funcionar desde GitHub
  (bloqueo de IPs de la nube), ejecútalo desde tu PC.
- Antes de pagar: informe de historial (Carfax / Carvertical), ITV/TÜV,
  libro de mantenimiento y nunca señales a vendedores sin verificar.
