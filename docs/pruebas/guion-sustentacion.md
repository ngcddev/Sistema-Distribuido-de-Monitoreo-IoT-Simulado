# Guion de sustentación — Tercer avance (AgroSense)

Orden de la demo según la rúbrica (§18). Cada bloque indica **quién lo presenta**, el **comando exacto** y
**qué se espera ver**. Todo se ejecuta desde la raíz del repositorio y contra el **API Gateway**
(`http://localhost:8000`); Home está en `http://localhost:8080`.

> **Terminal:** los comandos son de Bash. En Windows usar **Git Bash** (en PowerShell, `curl` es un alias de
> `Invoke-WebRequest`: escribir `curl.exe`). `jq` es opcional; sin él, quitar `| jq`.

## Reparto propuesto

| # | Bloque | Presenta | Tiempo aprox. |
|---|---|---|---|
| 0 | Preparación (antes de entrar) | Todo el equipo | — |
| 1 | Arquitectura | Nicolas Gaviria | 2 min |
| 2 | Docker Compose: `up -d --build` y `ps` | Nicolas Gaviria | 2 min |
| 3 | CRUD (Sensores, Mediciones, Umbrales) | Jainer Chocue | 3 min |
| 4 | Bases de datos y persistencia | Sebastián Paja | 3 min |
| 5 | Comunicación entre servicios | Jainer Chocue | 2 min |
| 6 | Error controlado y Timeout | Jainer Chocue | 2 min |
| 7 | Circuit Breaker (CLOSED → OPEN → HALF_OPEN → CLOSED) | Jainer Chocue | 3 min |
| 8 | Caída y recuperación de un servicio (§11: stop/start) | Sebastián Paja | 2 min |
| 9 | API Gateway | Nicolas Gaviria | 2 min |
| 10 | Home | Freyder Pacho | 2 min |
| 11 | GitHub (ramas, PR, issues, CI) | Freyder Pacho | 2 min |

*El reparto sigue los roles del README; ajustarlo si el equipo decide otra cosa.*

---

## 0. Preparación (antes de la sustentación)

```bash
git switch integracion/gateway-cb && git pull
cp .env.example .env            # si no existe
docker compose down             # sin -v: conserva los datos
docker compose up -d --build
```

- Dejar abiertas tres ventanas: una terminal para comandos, una terminal con el monitor del circuito
  (bloque 7) y el navegador en <http://localhost:8080>.
- Tener a mano Postman con las rutas de [docs/endpoints/postman-endpoints.txt](../endpoints/postman-endpoints.txt) por si se prefiere mostrar el CRUD ahí.
- Esperar a que todo esté `healthy` (≈ 1 min la primera vez).
- Comprobar que los puertos `8080` y `8000` están libres: si `home` no arranca con «Ports are not available»,
  otro programa usa el 8080 (`netstat -ano | grep ":8080 "`). Detenerlo o, solo para la demo, levantar
  Home en otro puerto: `docker run -d --rm --name home-demo --network red_iot -p 8081:80 sistema-distribuido-de-monitoreo-iot-simulado-home`.

## 1. Arquitectura — Nicolas

**Qué mostrar:** el diagrama del [README](../../README.md#arquitectura) y
[ARCHITECTURE.md](../arquitectura/ARCHITECTURE.md).

**Puntos a explicar:**

- Microservicios: Sensores, Mediciones, Monitoreo, más API Gateway, Home (Nginx) y Simulador.
- Una base MySQL por servicio; ningún servicio consulta la base de otro.
- Comunicación HTTP/REST con JSON dentro de la red `red_iot`.
- Solo se publican dos puertos: Home (`8080`) y Gateway (`8000`).
- Tolerancia a fallos: timeouts configurables y Circuit Breaker en Monitoreo.

## 2. Docker Compose — Nicolas

```bash
docker compose up -d --build
docker compose ps
```

**Se espera ver:** 9 contenedores `Up`: `mysql_sensores`, `mysql_mediciones`, `mysql_monitoreo`,
`sensores`, `mediciones`, `monitoreo`, `gateway`, `home` y `simulador`. Los que tienen API y los MySQL
aparecen `(healthy)`. Solo `gateway` (`0.0.0.0:8000->8000`) y `home` (`0.0.0.0:8080->80`) publican puertos.

```bash
curl -s localhost:8000/health | jq
```

**Se espera ver:** `{"gateway":"ok","servicios":{"sensores":"ok","mediciones":"ok","monitoreo":"ok"}}`.

## 3. CRUD — Jainer

Automático (recomendado, muestra cada solicitud con su código HTTP):

```bash
bash docs/pruebas/pruebas-integrales.sh crud
```

**Se espera ver**, para Sensores, Mediciones y Umbrales: `POST 201`, `GET 200`, `PUT 200`,
«la modificación quedó almacenada», `DELETE 200`, `GET` posterior `404`, id inexistente `404`. Al final:
validación `400` (tipo inválido), ruta desconocida `404` y `RESULTADO: todas las comprobaciones pasaron`.

Manual (si piden verlo paso a paso), con Sensores:

```bash
curl -s -X POST localhost:8000/sensores -H 'Content-Type: application/json' \
  -d '{"nombre":"Sensor demo","tipo":"humedad","ubicacion":"laboratorio","activo":true}'   # 201, anotar el id
curl -s localhost:8000/sensores/<id>                                                      # 200
curl -s -X PUT localhost:8000/sensores/<id> -H 'Content-Type: application/json' \
  -d '{"nombre":"Sensor demo editado","tipo":"humedad","ubicacion":"laboratorio","activo":false}'  # 200
curl -s -X DELETE localhost:8000/sensores/<id>                                            # 200
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/sensores/<id>                     # 404
```

## 4. Bases de datos y persistencia — Sebastián

**Qué mostrar:** [bases_datos/README.md](../../bases_datos/README.md) (una base por microservicio, con sus
tablas y operaciones) y los volúmenes:

```bash
docker volume ls | grep mysql_
docker compose exec mysql_sensores mysql -uroot -proot -e "SELECT * FROM sensores.sensores;"
docker compose exec mysql_mediciones mysql -uroot -proot -e "SELECT COUNT(*) FROM mediciones.mediciones;"
docker compose exec mysql_monitoreo mysql -uroot -proot -e "SHOW TABLES FROM monitoreo; SELECT * FROM monitoreo.umbrales;"
```

**Se espera ver:** tres volúmenes (`…_mysql_sensores_data`, `…_mysql_mediciones_data`,
`…_mysql_monitoreo_data`), los sensores iniciales, un conteo de mediciones que crece (el Simulador escribe
cada 5 s) y las tablas `umbrales` y `alertas`. (Si la contraseña de `.env` no es `root`, usar la de
`MYSQL_ROOT_PASSWORD`).

**Persistencia** (se recrean los contenedores de aplicación sin borrar volúmenes):

```bash
curl -s -X POST localhost:8000/sensores -H 'Content-Type: application/json' \
  -d '{"nombre":"Sensor persistente","tipo":"temperatura","ubicacion":"lab"}'   # anotar el id
docker compose rm -sf sensores mediciones monitoreo gateway home simulador
docker compose up -d
docker compose ps                                  # esperar a que gateway esté healthy
curl -s localhost:8000/sensores/<id>               # 200: el sensor sigue ahí
```

**Se espera ver:** el sensor creado antes de recrear los contenedores sigue existiendo. Explicar que solo
`docker compose down -v` borraría los datos.

## 5. Comunicación entre servicios — Jainer

```bash
bash docs/pruebas/pruebas-integrales.sh errores
```

o manualmente:

```bash
curl -s localhost:8000/monitoreo/resumen-general | jq   # Monitoreo -> GET /mediciones
curl -s localhost:8000/monitoreo/1 | jq                 # resumen de un sensor
curl -s localhost:8000/monitoreo/evaluar/1 | jq         # Monitoreo -> Mediciones + Sensores (tipo) + umbral
curl -s 'localhost:8000/monitoreo/alertas?limit=5' | jq
```

**Se espera ver:** `200` con totales y promedios calculados a partir de Mediciones; `evaluar` devuelve
`evaluacion` `NORMAL` o `ALERTA_CRITICA` y, si es alerta, aparece en `/monitoreo/alertas`. Explicar que
Monitoreo no toca la base de Mediciones ni la de Sensores: los consulta por HTTP.

## 6. Error controlado y Timeout — Jainer

Errores controlados (siempre JSON, nunca HTML):

```bash
curl -s -w '  -> %{http_code}\n' localhost:8000/ruta-inexistente                       # 404
curl -s -w '  -> %{http_code}\n' -X POST localhost:8000/sensores \
  -H 'Content-Type: application/json' -d '{"nombre":"x","tipo":"invalido"}'             # 400
```

Timeout (Monitoreo espera como máximo 3 s a Mediciones):

```bash
bash docs/pruebas/pruebas-integrales.sh timeout
```

o manualmente:

```bash
curl -s -X PUT localhost:8000/mediciones/simulacion/demora -H 'Content-Type: application/json' -d '{"segundos": 6}'
curl -s -w '  -> %{http_code}\n' localhost:8000/monitoreo/resumen-general     # 504 tras ~3 s
curl -s -X PUT localhost:8000/mediciones/simulacion/demora -H 'Content-Type: application/json' -d '{"segundos": 0}'
curl -s -w '  -> %{http_code}\n' localhost:8000/monitoreo/resumen-general     # 200
```

**Se espera ver:** `504` con `{"error":"El servicio de Mediciones no respondió a tiempo"}` y, al quitar la
demora, `200` de nuevo. Si el circuito llegó a abrirse, esperar 10 s antes de la última llamada.

## 7. Circuit Breaker — Jainer

En una segunda terminal, dejar corriendo el monitor del circuito:

```bash
while true; do curl -s localhost:8000/monitoreo/circuitos; echo; sleep 1; done
```

En la terminal principal:

```bash
bash docs/pruebas/pruebas-integrales.sh circuito
```

**Se espera ver (en orden):**

| Paso | Qué ocurre | Estado del circuito `mediciones` | Respuesta |
|---|---|---|---|
| 1 | Estado inicial | `CLOSED`, `contador_fallos: 0` | — |
| 2 | Se detiene Mediciones y se hacen 3 solicitudes | `CLOSED` 1 → 2 → `OPEN` | `503` (sin conexión) |
| 3 | Solicitud con el circuito abierto | `OPEN` | `503` «circuito abierto», sin llamar a Mediciones |
| 4 | Se reinicia Mediciones, todavía dentro de los 10 s | `OPEN` | `503` (el circuito sigue protegiendo) |
| 5 | Pasan 10 s (`CB_TIMEOUT`) | `HALF_OPEN` | la siguiente solicitud es la de prueba |
| 6 | La solicitud de prueba funciona | `CLOSED`, contador 0 | `200` |

Explicar los parámetros: `CB_MAX_FAILS=3`, `CB_TIMEOUT=10` s; los `404`/`400` no cuentan como falla.

## 8. Caída y recuperación de un servicio (§11) — Sebastián

Procedimiento de detener e iniciar un servicio y comprobar que solo fallan las operaciones que dependen de él:

```bash
curl -s -w '  -> %{http_code}\n' localhost:8000/sensores          # 200
docker compose stop sensores
docker compose ps sensores                                         # Exited
curl -s -w '  -> %{http_code}\n' localhost:8000/sensores          # 503 «el servicio de sensores no está disponible»
curl -s -w '  -> %{http_code}\n' 'localhost:8000/mediciones?limit=1'   # 200: Mediciones sigue funcionando
curl -s localhost:8000/monitoreo/evaluar/1 | jq                    # 200 con "advertencia": el tipo se dedujo de la unidad
docker compose start sensores
docker compose ps sensores                                         # esperar (healthy)
curl -s -w '  -> %{http_code}\n' localhost:8000/sensores          # 200: recuperado sin reiniciar nada más
```

Equivalente automático: `bash docs/pruebas/pruebas-integrales.sh caida`.

**Se espera ver:** con Sensores detenido, el Gateway responde `503` solo en `/sensores`; Mediciones sigue
en `200` y la evaluación de Monitoreo continúa con una advertencia. Al iniciarlo, todo vuelve a `200`.
En Home, la vista **Sensores** muestra el error y vuelve a cargar la tabla al pulsar «Actualizar lista».

## 9. API Gateway — Nicolas

```bash
curl -s localhost:8000/ | jq          # rutas que conoce el Gateway
curl -s localhost:8000/health | jq    # estado de cada servicio
docker compose ps --format '{{.Service}}\t{{.Ports}}'
```

**Se espera ver:** el Gateway enruta `/sensores`, `/mediciones` y `/monitoreo`; los microservicios no
publican puertos (solo `5001/tcp`, `5002/tcp`, `5003/tcp` internos). Explicar: conserva el código HTTP del
servicio, responde `404` a rutas desconocidas, `503` si el servicio está caído y `504` si supera
`GATEWAY_TIMEOUT=8` s. Todas las pruebas anteriores pasaron por `:8000`.

## 10. Home — Freyder

Abrir <http://localhost:8080> y recorrer:

1. **Vista general:** «Resumen General Global», «Evaluar Umbrales» del sensor 1, «Ver Alertas» y el gráfico.
2. **Sensores:** tabla cargada con `GET /sensores`; filtrar por tipo; registrar un sensor (POST);
   desactivarlo (PUT); eliminarlo (DELETE).
3. **Administración:** GET total y POST de una medición.

Con las herramientas del navegador (pestaña *Red*) mostrar que las peticiones van a `localhost:8080/sensores`,
`/mediciones` y `/monitoreo`: Nginx las reenvía al Gateway; el navegador nunca habla con un microservicio.

## 11. GitHub — Freyder

Mostrar en <https://github.com/ngcddev/Sistema-Distribuido-de-Monitoreo-IoT-Simulado>:

- Ramas por integrante y rama de integración `integracion/gateway-cb`.
- Pull Requests (#34) con revisión y los issues del tercer corte (#30–#33) enlazados.
- Pestaña **Actions**: el workflow de CI (validación de Compose, `pytest` de gateway y monitoreo y prueba
  de humo con el stack completo) en verde.
- Historial de commits con mensajes convencionales (`feat`, `fix`, `docs`, `test`).

---

## Si algo falla durante la demo

| Síntoma | Acción |
|---|---|
| Un contenedor no está `healthy` | `docker compose logs <servicio>` y `docker compose up -d <servicio>` |
| Monitoreo responde `503` «circuito abierto» sin motivo | Esperar 10 s y repetir (pasa a `HALF_OPEN`) |
| La demora de Mediciones quedó activa | `curl -X PUT localhost:8000/mediciones/simulacion/demora -H 'Content-Type: application/json' -d '{"segundos": 0}'` |
| Datos de una prueba anterior estorban | `docker compose down -v && docker compose up -d --build` (**borra los datos**) |
