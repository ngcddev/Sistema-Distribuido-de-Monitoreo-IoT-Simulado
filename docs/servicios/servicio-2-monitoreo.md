# Servicio 2: Monitoreo

## Resumen

API REST (Flask) que analiza las mediciones: calcula resúmenes por sensor y globales, administra los umbrales por tipo de sensor, evalúa las lecturas contra su umbral y registra alertas. Persiste umbrales y alertas en MySQL.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `monitoreo/app.py`, `monitoreo/database.py` |
| Framework | Flask (servido con gunicorn) |
| Puerto | `5002` |
| Contenedor Compose | `monitoreo` (API) y `evaluador` (worker `monitoreo/worker.py`, misma imagen) |
| Base de datos | `monitoreo` en el contenedor `mysql_monitoreo` |

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|---|---|---|---|
| GET | `/health` | Comprueba el servicio y la conexión a la BD | `200`, `503` |
| GET | `/monitoreo/<sensor_id>` | Resumen del sensor: cantidad, promedio y última lectura | `200`, `404` si no hay lecturas, `503` |
| GET | `/monitoreo/resumen-general` | Total de lecturas, sensores activos, listado y `promedios_por_unidad` | `200`, `503` |
| GET / POST | `/monitoreo/evaluar/<sensor_id>` | Compara la última lectura con el umbral de su tipo. `GET` solo consulta; `POST` además registra la alerta si está fuera de rango | `200`, `404`, `503` |
| GET | `/monitoreo/umbrales` | Lista los umbrales | `200` |
| GET | `/monitoreo/umbrales/<id>` | Obtiene un umbral | `200`, `404` |
| POST | `/monitoreo/umbrales` | Crea un umbral (`tipo`, `minimo`, `maximo`, `unidad` opcional) | `201`, `400`, `409` |
| PUT | `/monitoreo/umbrales/<id>` | Reemplaza un umbral | `200`, `400`, `404` |
| DELETE | `/monitoreo/umbrales/<id>` | Elimina un umbral | `200`, `404` |
| GET | `/monitoreo/alertas` | Lista alertas. Filtros: `sensor_id`, `limit` (por defecto 50, máx. 500) | `200`, `400` |
| DELETE | `/monitoreo/alertas/<id>` | Elimina una alerta | `200`, `404` |

`/monitoreo/evaluar/<sensor_id>` devuelve `evaluacion` = `NORMAL`, `ALERTA_CRITICA` o `SIN_UMBRAL`, y `alerta_registrada` (`true` solo con `POST` y fuera de rango). El tipo del sensor se obtiene del servicio Sensores; si no responde, se deduce de la unidad (`C` → temperatura, `%` → humedad). Se guarda una sola alerta por medición. Si Mediciones no está disponible, responde `503`.

## Evaluación automática (Evaluador)

El servicio `evaluador` ejecuta `monitoreo/worker.py`: al arrancar toma como punto de partida la última lectura existente y, cada `INTERVALO_EVALUACION_SEGUNDOS`, evalúa las lecturas posteriores (`GET /mediciones?desde_id=...`) y registra una alerta por cada una fuera de rango. Si Mediciones o la BD fallan, reintenta desde la última lectura procesada. No genera alertas del historial anterior a su arranque.

## Cambio de contrato

- `GET /monitoreo/<sensor_id>` devuelve **`404`** cuando el sensor no tiene lecturas.
- `/monitoreo/evaluar/<sensor_id>`: registrar una alerta escribe en la BD, así que ahora lo hace **`POST`**. `GET` sigue funcionando por compatibilidad, pero es de solo lectura (no registra la alerta).
- `resumen-general` y el resumen por sensor ya no descargan todas las lecturas: usan `GET /mediciones/estadisticas` de Mediciones.
- `resumen-general` **reemplaza `promedio_global_sistema` por `promedios_por_unidad`** (por ejemplo `{"C": 27.3, "%": 61.0}`): el promedio global mezclaba °C con % y no significaba nada.

## Base de datos

| Base | Tabla | Columnas |
|---|---|---|
| `monitoreo` | `umbrales` | `id` (PK), `tipo` VARCHAR(30) único, `minimo` DOUBLE, `maximo` DOUBLE, `unidad` VARCHAR(10) |
| `monitoreo` | `alertas` | `id` (PK), `medicion_id` INT único, `sensor_id` VARCHAR(50), `tipo`, `valor` DOUBLE, `estado`, `detalle`, `timestamp` DATETIME(3) en UTC |

Umbrales iniciales: temperatura 10–35 °C y humedad 30–80 %. Script de referencia: [`bases_datos/monitoreo.sql`](../../bases_datos/monitoreo.sql).

## Variables de entorno

| Variable | Descripción | Valor en Compose |
|---|---|---|
| `DB_HOST` | Host de MySQL | `mysql_monitoreo` |
| `DB_PORT` | Puerto de MySQL (opcional) | `3306` |
| `DB_USER` | Usuario de MySQL con permisos sobre su base | `DB_USER` del `.env` |
| `DB_PASSWORD` | Contraseña de MySQL | `DB_PASSWORD` del `.env` |
| `DB_NAME` | Nombre de la base | `monitoreo` |
| `MEDICIONES_URL` | URL del servicio Mediciones | `http://mediciones:5001` |
| `SENSORES_URL` | URL del servicio Sensores | `http://sensores:5003` |
| `INTERVALO_EVALUACION_SEGUNDOS` | Solo `evaluador`: segundos entre ciclos | `10` |

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Monitoreo | Mediciones | `GET /mediciones?sensor_id=X&limit=N` | `sensor_id`, `limit` | Lista de mediciones |
| Monitoreo | Mediciones | `GET /mediciones/estadisticas[?sensor_id=X]` | `sensor_id` opcional | `total`, `sensores`, `por_unidad` (y `promedio` si hay `sensor_id`) |
| Evaluador | Mediciones | `GET /mediciones?desde_id=N&limit=1000` | último id evaluado | Lecturas nuevas |
| Monitoreo | Sensores | `GET /sensores/<id>` | `id` del sensor | Sensor con su `tipo` |
| Home (Nginx) | Monitoreo | `/monitoreo/...` | Petición del navegador | JSON de la API |

## Ejecución

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build monitoreo
curl -X POST http://localhost:5002/monitoreo/evaluar/1
```
