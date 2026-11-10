# Seguimiento de la auditoría

Registro de los cambios aplicados tras la auditoría y de **cuáles necesitan supervisión humana**.

**Qué significa "supervisar":** el cambio se hizo y las pruebas automáticas pasan, pero hay algo que
esas pruebas no pueden confirmar (el stack real con Docker, un navegador, una decisión de producto).
Las 133 pruebas de `pytest` usan una base de datos simulada, pero el CI del PR #27 ya ejecutó el stack
completo en Docker real (ver «Verificado en Docker»).

**Ya verificado sin Docker:** las 133 pruebas de `pytest`, 25 pruebas del Home en Chrome real (CSP estricta sin
violaciones, escritura con y sin credenciales, navegación por URL, gráfico y su refresco, confirmación al borrar, error de red, datos de la API
mostrados como texto, encabezados, metadatos), la sintaxis
SQL (21 sentencias, dialecto MySQL), la sintaxis y los contextos de las directivas de `nginx.conf`, el YAML de
compose/CI y `ruff`.

## Verificado en Docker (CI, PR #27)

El job «Stack completo con Docker Compose» (1 min 30 s, ejecución 42915408386; **7 de 7 checks en verde**) hizo, con
contenedores reales:

- Construyó las cinco imágenes y descargó `mysql:8.4` y `nginxinc/nginx-unprivileged:1.28-alpine`.
- Levantó los **10 contenedores** y todos llegaron a `Healthy` con `docker compose up --wait`.
- `/health` de las tres APIs, y Home llegando a ellas a través del proxy de Nginx.
- **Autenticación de escritura con el Nginx real**: `POST` y `DELETE` sin credenciales o con una clave equivocada
  dan `401`; con las correctas la escritura funciona. Eso prueba que `15-credenciales.sh` se ejecuta al arrancar.
- Un sensor inexistente se rechaza (`400`); alta de lecturas y `/mediciones/estadisticas` sobre MySQL 8.4 con
  `DATETIME(3)` y el conector 9.1; gunicorn con el usuario sin privilegios; Chart.js local y la cabecera
  `X-Content-Type-Options` servidos por el Nginx real.

**Lo que esa ejecución no comprobó** (los contenedores arrancaron, pero no se miró su efecto): que el purgador borre
lecturas antiguas y que el evaluador cree alertas solo. La prueba de humo se amplió con ambas comprobaciones y con la
CSP estricta; se confirmarán en la siguiente ejecución del CI. Tampoco se ha probado el reinicio ante un fallo de la
base de datos (H5) ni el del simulador (H9).

Avisos cosméticos en el log, sin efecto: `useradd` avisa de que el uid 10001 sale del rango de usuarios de sistema,
`pip` avisa de que se ejecuta como `root` durante la construcción y `actions/checkout@v4` usa Node 20 (en desuso).

> **Prueba manual opcional:** `cp .env.example .env`, `docker compose down -v` (borra datos) y
> `docker compose up --build`; el Home queda en <http://localhost:8080>.

## Prioridad alta

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| H1 | Solo Home publicado; puertos de APIs en `compose.dev.yaml`; **escribir exige credenciales** (Basic en Nginx; consultar y evaluar son libres) | Hecho | No | **Verificado en Docker (CI):** el contenedor arranca, el script de credenciales se ejecuta y las reglas de Nginx dan `401` sin credenciales y dejan escribir con ellas. Límites asumidos: HTTP sin cifrar y una sola cuenta; los puertos de `compose.dev.yaml` siguen sin protección. |
| H2 | Usuario de BD por servicio, sin `root` | Hecho | No | **Verificado en Docker (CI):** con `DB_USER` distinto de `root` los servicios crean sus tablas y atienden peticiones. Recordatorio: hay que recrear los volúmenes existentes. |
| H3 | Healthchecks, `service_healthy`, `restart` | Hecho | No | **Verificado en Docker (CI):** los 10 contenedores llegan a `healthy` con `up --wait`. |
| H4 | gunicorn + inicialización en `on_starting` | Hecho | No | **Verificado en Docker (CI):** gunicorn arranca y responde `/health` en las tres APIs. |
| H5 | El proceso termina si la BD no queda lista | Hecho | **Sí** | El arranque normal está verificado; falta el camino de fallo. Parar `mysql_mediciones` y reiniciar `mediciones`: debe fallar y reiniciarse, no quedar vivo sin tablas. |
| H6 | Consultas acotadas, `/estadisticas`, `desde_id` y **retención de 30 días** (servicio `purgador` para lecturas; el Evaluador purga alertas) | Hecho | **Sí** | El purgador arranca en Docker, pero su efecto solo está probado con base simulada. La prueba de humo del CI se amplió (lectura de hace 60 días con `PURGA_INTERVALO_SEGUNDOS=5`) y hay que ver esa ejecución en verde. `RETENCION_DIAS=0` desactiva el borrado. |
| H7 | Evaluador automático + `POST` para evaluar | Hecho | **Sí** | El evaluador arranca en Docker, pero que cree alertas solo aún no se ha visto en ejecución real: la prueba de humo ampliada lo comprueba (lectura de 91.234 °C y espera de su alerta). Arranca "desde ahora": no genera alertas del historial previo. |
| H8 | Pruebas y CI | Hecho | No | **CI ejecutado en el PR #27: 7 de 7 checks en verde**, incluidas las 25 pruebas de navegador con el Chrome del runner. |
| H9 | El simulador sale con error si Mediciones no responde | Hecho | No | Opcional: `docker compose stop mediciones` y ver que el simulador se reinicia. |
| H10 | Quitar "alta disponibilidad" del Home | Hecho | No | — |

## Prioridad media

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| M1 | `timestamp` como `DATETIME(3)` en UTC (+ índice) | Hecho | No | **Verificado en Docker (CI):** alta y consulta sobre MySQL 8.4 con `DATETIME(3)`. **No hay migración**: requiere recrear volúmenes. |
| M2 | Mediciones valida el sensor contra Sensores | Hecho | No | **Verificado en Docker (CI):** un sensor inexistente da `400`. Ids no numéricos también; si Sensores cae, la lectura se acepta (decisión de diseño). |
| M3 | Alertas "huérfanas" al borrar una medición | Documentado | No | Se decidió que la alerta es un registro histórico. Confirmar que el equipo está de acuerdo. |
| M4 | `INTERVALO_SEGUNDOS` llegaba al simulador | Hecho (en alta) | No | — |
| M5 | Errores de BD: 503 solo si no hay conexión, 500 en otro caso, con log | Hecho | No | — |
| M6 | PUT/PATCH/DELETE de mediciones | Resuelto | No | Decisión: se mantienen, pero solo con credenciales (ver H1). Queda anotado en ARCHITECTURE que, en producción, la telemetría suele ser inmutable. |
| M7 | `timestamp` opcional enviado por el sensor | Hecho | No | — |
| M8 | Prueba que impide que `bases_datos/*.sql` se desincronice | Hecho | No | — |
| M9 | Imágenes fijadas; MySQL 8.0 → 8.4 | Hecho | No | **Verificado en Docker (CI):** las imágenes se descargan y el conector 9.1 conecta con MySQL 8.4. |
| M10 | Contenedores sin root; Home en `nginx-unprivileged` (8080) | Hecho | No | **Verificado en Docker (CI):** Home responde en `8080` y gunicorn arranca con el usuario `app`. |
| M11 | Cabeceras de seguridad, gzip, rutas del proxy más estrictas | Hecho | **Sí** | `X-Content-Type-Options` verificado en el Nginx real (CI). La CSP se probó en Chrome real con las cabeceras leídas de `nginx.conf`; la prueba de humo ampliada comprobará la cabecera del Nginx real en la siguiente ejecución. |
| M12 | CI: lint, `push` a `main`, Dependabot | Hecho | **Sí** | **Primera ejecución en GitHub: 7 de 7 en verde.** Dependabot empezará a actuar cuando `dependabot.yml` esté en `main`. |
| M13 | `try/catch` en las operaciones del Home | Hecho | No | Verificado en navegador (error de red → mensaje claro). |
| M14 | Confirmación antes de borrar | Hecho | No | Verificado en navegador (cancelar no borra; aceptar borra). |
| M15 | `aria-live` en estados y resultados | Hecho | No | — |
| M16 | Colores de estado con contraste suficiente | Hecho | No | — |
| M17 | Diseño responsive | **Diferido** | — | Se hará en la fase de diseño. |
| M18 | Menú con enlaces reales y vista en la URL | Hecho | No | Verificado en navegador: `#administracion`, botón atrás y apertura directa. |
| M19 | Chart.js local (sin CDN) | Hecho | No | Verificado en navegador: carga sin CDN. Archivo: `home/vendor/chart.umd.min.js` (4.4.1, MIT). SHA-256 `d2af8974e95271638772e9e9524db5b9a6f58d6ec2d5d781400447b4a31c681e`. |
| M20 | El gráfico se refresca cada 10 s | Hecho | No | Verificado en navegador (se vuelve a pedir a los 10 s). |

## Prioridad baja (soft)

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| S1–S6 | Identidad visual, tarjetas y tablas en lugar de texto, elementos decorativos sin función, umbrales en el gráfico, textos de los botones, selector de sensores | **Diferido** | — | Van en la fase de diseño, como se acordó. |
| S7 | Sin estilos en línea: clases y variables CSS | Hecho | No | Verificado en navegador: ningún elemento (salvo el `<canvas>` de Chart.js) lleva `style`. |
| S8 | CSS sin reglas muertas | Hecho | No | — |
| S9 | `…` en lugar de `...`, idioma `es` en las horas, etiqueta de respaldo `—` | Hecho | No | — |
| S10 | Los datos de la API se insertan como texto (`textContent`), no con `innerHTML` | Hecho | No | Prueba con payload malicioso; se comprobó que falla si se vuelve a `innerHTML`. |
| S11 | Metadatos (`description`, `theme-color`, `color-scheme`), favicon, un único `h1` y encabezados sin saltos | Hecho | No | Verificado en navegador. |
| S12 | Sin código repetido dentro de un servicio (`validar_medicion` en POST y PUT) | Hecho | No | Entre servicios se repite a propósito: ver ARCHITECTURE. |
| S13 | Rutas equivalentes de Mediciones | Documentado | No | Se mantienen por compatibilidad (ver docs del servicio). |
| S14 | `logging` en lugar de `print()`, sesión HTTP reutilizada en el simulador | Hecho | No | — |
| S15 | `limit`/`id` con dígitos no ASCII dan `400` | Hecho | No | — |
| S16 | Archivos `compose.yaml` y `compose.dev.yaml` | Hecho | **Sí** | Ahora los comandos usan `-f compose.yaml -f compose.dev.yaml`. Una sola instancia de MySQL con tres bases **no** se hizo: se mantiene una por servicio (decisión de diseño). |
| — | Foco visible, estados hover, `aria-current`, `translate="no"`, `name`/`autocomplete` en los campos, `defer` en los scripts, CSP sin `unsafe-inline` | Hecho | **Sí** | La CSP estricta se probó en Chrome real; el CI ampliado comprobará la cabecera en el Nginx real. |
| — | Pruebas del simulador (13) y en el CI | Hecho | No | — |

## Mantenimiento (revisión posterior)

| Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|
| `puppeteer-core` 23 → 25.17 (0 vulnerabilidades en `npm audit`; antes 9 altas, solo en herramientas de prueba) y Node 22 en el CI | Hecho | No | Verificado con `npm ci` y las 15 pruebas. La versión 25 exige Node ≥ 22.12 (`engines` en `package.json`). |
| Dependabot cubre todos los Dockerfile, `compose.yaml`, `home/e2e` (npm) y la raíz (`requirements-dev.txt`) | Hecho | **Sí** | Se valida al fusionar en `main` (Dependabot lee el archivo de la rama por defecto); la ecosistema `docker-compose` no se ha podido probar. |
| Chart.js documentado en `home/vendor/README.md` (versión, licencia, SHA-256 y cómo actualizar) | Hecho | No | Dependabot no actualiza archivos copiados: es manual. |
| `.gitattributes` con LF en todo el repositorio | Hecho | No | Elimina los avisos de CRLF; renormalizar no modificó ningún archivo existente. |

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| H1 | Escritura con contraseña: consultar libre, crear/modificar/borrar con credenciales (excepto evaluar un sensor). |
| H6 | Se conservan 30 días de lecturas y alertas, configurable con `RETENCION_DIAS`. |
| M6 | Las lecturas se pueden editar y borrar, pero solo con credenciales. |

## Para la fase de diseño

Quedan `S1`–`S6` y el responsive (`M17`): el rediseño visual del Home va al final, como se acordó.
