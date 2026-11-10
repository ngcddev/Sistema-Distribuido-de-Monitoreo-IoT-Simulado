# Seguimiento de la auditoría

Registro de los cambios aplicados tras la auditoría y de **cuáles necesitan supervisión humana**.

**Qué significa "supervisar":** el cambio se hizo y las pruebas automáticas pasan, pero hay algo que
esas pruebas no pueden confirmar (el stack real con Docker, un navegador, una decisión de producto).
Las 133 pruebas de `pytest` usan una base de datos simulada; el workflow de CI todavía no se ha ejecutado.

**Ya verificado sin Docker:** las 133 pruebas de `pytest`, 25 pruebas del Home en Chrome real (CSP estricta sin
violaciones, escritura con y sin credenciales, navegación por URL, gráfico y su refresco, confirmación al borrar, error de red, datos de la API
mostrados como texto, encabezados, metadatos), la sintaxis
SQL (21 sentencias, dialecto MySQL), la sintaxis y los contextos de las directivas de `nginx.conf`, el YAML de
compose/CI y `ruff`. **No verificable sin Docker:** el arranque real de los contenedores, MySQL 8.4,
gunicorn y Nginx en ejecución.

> **Primera verificación recomendada:** `cp .env.example .env`, recrear volúmenes
> (`docker compose down -v`, borra datos) y `docker compose up --build`. Si todo queda `healthy` y el
> Home carga en <http://localhost:8080>, la mayoría de los puntos de abajo quedan confirmados.

## Prioridad alta

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| H1 | Solo Home publicado; puertos de APIs en `compose.dev.yaml`; **escribir exige credenciales** (Basic en Nginx; consultar y evaluar son libres) | Hecho | **Sí** | **No se pudo ejecutar Nginx.** Se validó la sintaxis, el script de arranque y el contrato de `nginx.conf` con pruebas y mutación, pero hay que comprobar con Docker que (1) el contenedor arranca y `15-credenciales.sh` se ejecuta, (2) `POST` sin credenciales da `401` y con ellas funciona. Límites asumidos: HTTP sin cifrar y una sola cuenta. Los puertos de `compose.dev.yaml` siguen sin protección. |
| H2 | Usuario de BD por servicio, sin `root` | Hecho | **Sí** | Recrear volúmenes. Revisar en los logs `base de datos lista` y que el usuario pueda crear sus tablas. |
| H3 | Healthchecks, `service_healthy`, `restart` | Hecho | **Sí** | No probado con Docker. Comprobar que todo llega a `healthy` y que los tiempos (`start_period`) alcanzan en tu máquina. |
| H4 | gunicorn + inicialización en `on_starting` | Hecho | **Sí** | No probado. Comprobar que la BD se prepara una sola vez (no por worker). |
| H5 | El proceso termina si la BD no queda lista | Hecho | **Sí** | Parar `mysql_mediciones` y reiniciar `mediciones`: debe fallar y reiniciarse, no quedar vivo sin tablas. |
| H6 | Consultas acotadas, `/estadisticas`, `desde_id` y **retención de 30 días** (servicio `purgador` para lecturas; el Evaluador purga alertas) | Hecho | **Sí** | Probado con base simulada. Con Docker: bajar `PURGA_INTERVALO_SEGUNDOS`, crear una lectura con `timestamp` antiguo y ver que desaparece. Cambiar `RETENCION_DIAS` en `.env` (`0` desactiva el borrado). |
| H7 | Evaluador automático + `POST` para evaluar | Hecho | **Sí** | Comprobar que aparecen alertas sin pulsar nada. El evaluador arranca "desde ahora": no genera alertas del historial previo. |
| H8 | Pruebas y CI | Hecho | **Sí** | Ahora hay pruebas del Home en navegador (`home/e2e`, 25 pruebas). Falta ejecutar el CI en un PR real y confirmar que pasa (incluido el job del Home con el Chrome del runner). |
| H9 | El simulador sale con error si Mediciones no responde | Hecho | No | Opcional: `docker compose stop mediciones` y ver que el simulador se reinicia. |
| H10 | Quitar "alta disponibilidad" del Home | Hecho | No | — |

## Prioridad media

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| M1 | `timestamp` como `DATETIME(3)` en UTC (+ índice) | Hecho | **Sí** | **No hay migración**: requiere recrear volúmenes. Con MySQL real, comprobar un `POST` y un `GET` (formato ISO) y que las alertas guardan su fecha. |
| M2 | Mediciones valida el sensor contra Sensores | Hecho | **Sí** | Cambia el comportamiento: ids no numéricos o inexistentes dan `400`. Si Sensores cae, la lectura se acepta (decisión de diseño). |
| M3 | Alertas "huérfanas" al borrar una medición | Documentado | No | Se decidió que la alerta es un registro histórico. Confirmar que el equipo está de acuerdo. |
| M4 | `INTERVALO_SEGUNDOS` llegaba al simulador | Hecho (en alta) | No | — |
| M5 | Errores de BD: 503 solo si no hay conexión, 500 en otro caso, con log | Hecho | No | — |
| M6 | PUT/PATCH/DELETE de mediciones | Resuelto | No | Decisión: se mantienen, pero solo con credenciales (ver H1). Queda anotado en ARCHITECTURE que, en producción, la telemetría suele ser inmutable. |
| M7 | `timestamp` opcional enviado por el sensor | Hecho | No | — |
| M8 | Prueba que impide que `bases_datos/*.sql` se desincronice | Hecho | No | — |
| M9 | Imágenes fijadas; MySQL 8.0 → 8.4 | Hecho | **Sí** | Las etiquetas `mysql:8.4` y `nginxinc/nginx-unprivileged:1.28-alpine` no se han descargado aún. Comprobar la conexión del conector 9.1 con la autenticación por defecto de 8.4. |
| M10 | Contenedores sin root; Home en `nginx-unprivileged` (8080) | Hecho | **Sí** | Comprobar que Home responde en `8080` y que gunicorn arranca con el usuario `app`. |
| M11 | Cabeceras de seguridad, gzip, rutas del proxy más estrictas | Hecho | **Sí** | La CSP se probó en Chrome real (sin violaciones y bloqueando scripts en línea) con las cabeceras leídas de `nginx.conf`. Falta confirmarlo con el Nginx real. |
| M12 | CI: lint, `push` a `main`, Dependabot | Hecho | **Sí** | Primera ejecución en GitHub. Activar Dependabot si el repositorio lo permite. |
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
| — | Foco visible, estados hover, `aria-current`, `translate="no"`, `name`/`autocomplete` en los campos, `defer` en los scripts, CSP sin `unsafe-inline` | Hecho | **Sí** | La CSP estricta se probó en Chrome real; falta confirmarla con el Nginx real. |
| — | Pruebas del simulador (13) y en el CI | Hecho | No | — |

## Mantenimiento (revisión posterior)

| Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|
| `puppeteer-core` 23 → 25.17 (0 vulnerabilidades en `npm audit`; antes 9 altas, solo en herramientas de prueba) y Node 22 en el CI | Hecho | No | Verificado con `npm ci` y las 15 pruebas. La versión 25 exige Node ≥ 22.12 (`engines` en `package.json`). |
| Dependabot cubre todos los Dockerfile, `compose.yaml`, `home/e2e` (npm) y la raíz (`requirements-dev.txt`) | Hecho | **Sí** | Se valida cuando el repositorio esté en GitHub; la ecosistema `docker-compose` no se ha podido probar aquí. |
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
