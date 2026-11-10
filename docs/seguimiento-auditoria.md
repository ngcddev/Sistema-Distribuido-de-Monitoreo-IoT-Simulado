# Seguimiento de la auditoría

Registro de los cambios aplicados tras la auditoría y de **cuáles necesitan supervisión humana**.

**Qué significa "supervisar":** el cambio se hizo y las pruebas automáticas pasan, pero hay algo que
esas pruebas no pueden confirmar (el stack real con Docker, un navegador, una decisión de producto).
Las 107 pruebas de `pytest` usan una base de datos simulada; el workflow de CI todavía no se ha ejecutado.

**Ya verificado sin Docker:** las 107 pruebas de `pytest`, 10 pruebas del Home en Chrome real (CSP sin
violaciones, navegación por URL, gráfico y su refresco, confirmación al borrar, error de red), la sintaxis
SQL (21 sentencias, dialecto MySQL), la sintaxis y los contextos de las directivas de `nginx.conf`, el YAML de
compose/CI y `ruff`. **No verificable sin Docker:** el arranque real de los contenedores, MySQL 8.4,
gunicorn y Nginx en ejecución.

> **Primera verificación recomendada:** `cp .env.example .env`, recrear volúmenes
> (`docker compose down -v`, borra datos) y `docker compose up --build`. Si todo queda `healthy` y el
> Home carga en <http://localhost:8080>, la mayoría de los puntos de abajo quedan confirmados.

## Prioridad alta

| # | Cambio | Estado | ¿Supervisar? | Qué verificar |
|---|---|---|---|---|
| H1 | Solo Home publicado; puertos de APIs en `docker-compose.dev.yml` | **Parcial** | **Sí (decisión)** | Sigue **sin autenticación** y Nginx deja pasar PUT/DELETE. Decidir cómo proteger las rutas de escritura (clave de API, login, solo lectura en Home). |
| H2 | Usuario de BD por servicio, sin `root` | Hecho | **Sí** | Recrear volúmenes. Revisar en los logs `base de datos lista` y que el usuario pueda crear sus tablas. |
| H3 | Healthchecks, `service_healthy`, `restart` | Hecho | **Sí** | No probado con Docker. Comprobar que todo llega a `healthy` y que los tiempos (`start_period`) alcanzan en tu máquina. |
| H4 | gunicorn + inicialización en `on_starting` | Hecho | **Sí** | No probado. Comprobar que la BD se prepara una sola vez (no por worker). |
| H5 | El proceso termina si la BD no queda lista | Hecho | **Sí** | Parar `mysql_mediciones` y reiniciar `mediciones`: debe fallar y reiniciarse, no quedar vivo sin tablas. |
| H6 | Consultas acotadas, `/estadisticas`, `desde_id` | **Parcial** | **Sí (decisión)** | **Falta la retención** de datos antiguos (la tabla crece sin límite). Con `DATETIME` e índice por fecha ya es posible; falta decidir cuántos días y quién ejecuta el borrado. |
| H7 | Evaluador automático + `POST` para evaluar | Hecho | **Sí** | Comprobar que aparecen alertas sin pulsar nada. El evaluador arranca "desde ahora": no genera alertas del historial previo. |
| H8 | Pruebas y CI | Hecho | **Sí** | Ahora hay pruebas del Home en navegador (`home/e2e`, 10 pruebas). Falta ejecutar el CI en un PR real y confirmar que pasa (incluido el job del Home con el Chrome del runner). |
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
| M6 | PUT/DELETE de mediciones (¿telemetría inmutable?) | **Pendiente** | **Sí (decisión)** | Decisión de producto; se mantiene como está. |
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

## Para la fase soft y de diseño

Quedan los puntos soft (`S1`–`S16`) y la parte visual. El rediseño del Home y el responsive (M17) van
al final, como se acordó.
