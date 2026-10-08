# Radar de chollos — coches de segunda mano ES + DE

Cada mañana revisa **AutoScout24** (España y Alemania), **coches.net** (España) y
**Autohero** (España y Alemania) buscando Audi, BMW, Mercedes-Benz, Volkswagen,
Toyota y Mazda de **≤ 55.000 km**, **publicados en las últimas 24 h**, de
**profesionales con garantía**, que estén claramente por debajo de mercado.
Publica un informe web con fotos, descuento, coste puesto en España y bajadas de precio.

Filtros especiales:
- **Alemania**: solo coches que pagarían **0 % de impuesto de matriculación** en España
  (CO2 ≤ 120 g/km WLTP, o eléctricos). Si el anuncio no indica el CO2, se descarta.
- **Concesionarios excluidos**: Flexicar (lista editable en `vendedores_excluidos`).

## Cómo decide qué es una oportunidad

1. **Lee los portales**: anuncios recientes (para conocer el mercado) y los
   publicados en las últimas 24 h (los candidatos).
2. **Junta duplicados**: si el mismo coche está en varios portales sale una vez,
   con todos los enlaces.
3. **Valora el mercado**: para cada modelo y país ajusta un modelo de precio
   (antigüedad, km y potencia) con los anuncios de todos los portales.
4. **Comprueba la garantía** (≥ 12 meses): en la ficha (AutoScout24), en el
   anuncio (coches.net) o incluida siempre (Autohero).
5. **Descuento** = media entre nuestro modelo y la referencia del portal
   (mediana de AutoScout24 o precio medio de coches.net). Para coches alemanes
   calcula el **coste puesto en España** (transporte + ITV/gestoría/placas +
   impuesto de matriculación según CO2) y lo compara con el precio en España.
6. Puntúa y marca como **Revisar** lo que esté > 35 % por debajo (posible error o fraude).

Todo se ajusta en [`config.toml`](config.toml).

## Paso a paso para ponerlo en la nube (GitHub, gratis)

1. **Cuenta**: regístrate en <https://github.com/signup>.
2. **Repositorio**: arriba a la derecha **+ → New repository** · nombre
   `radar-coches` · **Public** · **Create repository**.
3. **Subir archivos**:
   - En el Explorador de Windows activa **Vista → Mostrar → Elementos ocultos**
     (si no, no verás la carpeta `.github`, que es la que programa la ejecución diaria).
   - En GitHub pulsa **uploading an existing file**, selecciona todo el contenido
     de la carpeta `rastreador-coches` y arrástralo. **Commit changes**.
   - Comprueba que existe `.github/workflows/diario.yml` en el repositorio. Si no:
     **Add file → Create new file**, nombre `.github/workflows/diario.yml`, pega su
     contenido y guarda.
4. **Activar la web**: **Settings → Pages → Source: GitHub Actions**.
5. **Primera ejecución**: **Actions** (acepta si lo pide) → **Rastreo diario** →
   **Run workflow**. Tarda ~15-20 min. ✅ verde = funciona; ❌ rojo = abre la
   ejecución, copia el error y pásamelo.
6. **Tu informe**: `https://TU-USUARIO.github.io/radar-coches/` (también aparece
   en Settings → Pages). Guárdalo en el móvil; se actualiza cada día a las 7:30.
7. **Cambiar filtros**: abre `config.toml` en GitHub, lápiz ✏️, cambia y *Commit*.

## Avisos por Telegram

Tras cada ejecución te llega un mensaje con las oportunidades **nuevas** que superen
el descuento del aviso (12 % por defecto, en `[aviso]` de `config.toml`): foto,
precio, descuento, garantía, coste puesto en España y enlace. Nunca repite un coche.

1. **Crea el bot**: en Telegram abre **@BotFather** → `/newbot` → ponle un nombre
   (p. ej. `Radar de chollos`) y un usuario acabado en `bot` (p. ej. `radar_chollos_mc_bot`).
   Te dará un **token** como `123456789:AAH...`. No lo compartas con nadie.
2. **Abre tu bot** (el enlace `t.me/...` que te da BotFather) y pulsa **Iniciar**.
   Sin esto el bot no puede escribirte.
3. **Tu id**: abre **@userinfobot**, pulsa **Iniciar** y copia el número de `Id`.
4. **Guárdalos en GitHub**: en tu repositorio **Settings → Secrets and variables →
   Actions → New repository secret**, crea dos:
   - Nombre `TELEGRAM_TOKEN` → valor: el token del paso 1.
   - Nombre `TELEGRAM_CHAT_ID` → valor: el número del paso 3.
5. **Prueba**: **Actions → Rastreo diario → Run workflow**, marca
   **«Solo enviar un mensaje de prueba a Telegram»** → **Run workflow**. En un minuto
   debe llegarte «✅ Radar de chollos conectado».

## Ejecutarlo en tu PC

```
python rastreador.py            # completo
python rastreador.py --rapido   # prueba rápida
```

Abre `docs/index.html`. Solo necesita Python 3.11+ (sin librerías extra).

## Avisos

- **coches.net** tiene protección anti-bots. El rastreador hace muy pocas
  consultas, muy espaciadas, y si aparece la página de bloqueo deja ese portal
  ese día y sigue con los demás (el informe muestra el estado de cada portal).
- **Autohero** no publica fecha de anuncio: cuenta como «publicado hoy» el primer
  día que el rastreador lo ve (desde la segunda ejecución).
- **heycar** ya no opera en Alemania (redirige a un portal británico), por eso no está.
- **mobile.de** rechaza cualquier acceso automatizado ("Zugriff verweigert"), así que
  no está incluido. Alternativa: en la app de mobile.de guarda una búsqueda
  (Händler, ≤ 55.000 km, tus marcas) y activa sus avisos push. Además, buena parte
  de los concesionarios alemanes publican también en AutoScout24.de.
- Los costes de importación son **estimaciones** (Hacienda calcula el impuesto con
  sus tablas, no con el precio de compra). Pide presupuesto antes de comprar.
- Las condiciones de uso de estos portales restringen el acceso automatizado. El
  rastreador hace pocas peticiones, con pausas, para uso personal.
- Antes de pagar: informe de historial (Carfax / carVertical), ITV/TÜV, libro de
  mantenimiento, y nunca adelantes dinero a vendedores sin verificar.
