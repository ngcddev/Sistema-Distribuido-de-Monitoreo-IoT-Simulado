# Servicio 2: Monitoreo

## Resumen

API REST (Flask) que analiza las mediciones: calcula resúmenes por sensor y globales, administra los umbrales por tipo de sensor, evalúa la última lectura contra su umbral y registra alertas. Persiste umbrales y alertas en MySQL.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `monitoreo/app.py`, `monitoreo/database.py` |
| Framework | Flask |
| Puerto | `5002` |
| Contenedor Compose | `monitoreo` |
| Base de datos | `monitoreo` en el contenedor `mysql_monitoreo` |

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|---|---|---|---|
| GET | `/health` | Comprueba el servicio y la conexión a la BD | `200`, `503` |
| GET | `/monitoreo/<sensor_id>` | Resumen del sensor: cantidad, promedio y última lectura | `200`, `404` si no hay lecturas, `503` |
| GET | `/monitoreo/resumen-general` | Total de lecturas, sensores activos, listado y promedio global | `200`, `503` |
| GET | `/monitoreo/evaluar/<sensor_id>` | Compara la última lectura con el umbral de su tipo; si está fuera de rango registra una alerta | `200`, `404`, `503` |
| GET | `/monitoreo/umbrales` | Lista los umbrales | `200` |
| GET | `/monitoreo/umbrales/<id>` | Obtiene un umbral | `200`, `404` |
| POST | `/monitoreo/umbrales` | Crea un umbral (`tipo`, `minimo`, `maximo`, `unidad` opcional) | `201`, `400`, `409` |
| PUT | `/monitoreo/umbrales/<id>` | Reemplaza un umbral | `200`, `400`, `404` |
| DELETE | `/monitoreo/umbrales/<id>` | Elimina un umbral | `200`, `404` |
| GET | `/monitoreo/alertas` | Lista alertas. Filtros: `sensor_id`, `limit` (por defecto 50, máx. 500) | `200`, `400` |
| DELETE | `/monitoreo/alertas/<id>` | Elimina una alerta | `200`, `404` |

`/monitoreo/evaluar/<sensor_id>` devuelve `evaluacion` = `NORMAL`, `ALERTA_CRITICA` o `SIN_UMBRAL`. El tipo del sensor se obtiene del servicio Sensores; si no responde, se deduce de la unidad (`C` → temperatura, `%` → humedad). Se guarda una sola alerta por medición. Si Mediciones no está disponible, responde `503`.

## Cambio de contrato

`GET /monitoreo/<sensor_id>` devuelve **`404`** cuando el sensor no tiene lecturas.

## Base de datos

| Base | Tabla | Columnas |
|---|---|---|
| `monitoreo` | `umbrales` | `id` (PK), `tipo` VARCHAR(30) único, `minimo` DOUBLE, `maximo` DOUBLE, `unidad` VARCHAR(10) |
| `monitoreo` | `alertas` | `id` (PK), `medicion_id` INT único, `sensor_id` VARCHAR(50), `tipo`, `valor` DOUBLE, `estado`, `detalle`, `timestamp` |

Umbrales iniciales: temperatura 10–35 °C y humedad 30–80 %. Script de referencia: [`bases_datos/monitoreo.sql`](../../bases_datos/monitoreo.sql).

## Variables de entorno

| Variable | Descripción | Valor en Compose |
|---|---|---|
| `DB_HOST` | Host de MySQL | `mysql_monitoreo` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `DB_USER` | Usuario de MySQL (necesita `CREATE`) | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `root` |
| `DB_NAME` | Nombre de la base | `monitoreo` |
| `MEDICIONES_URL` | URL del servicio Mediciones | `http://mediciones:5001` |
| `SENSORES_URL` | URL del servicio Sensores | `http://sensores:5003` |

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Monitoreo | Mediciones | `GET /mediciones?sensor_id=X&limit=N` | `sensor_id`, `limit` | Lista de mediciones |
| Monitoreo | Sensores | `GET /sensores/<id>` | `id` del sensor | Sensor con su `tipo` |
| Home (Nginx) | Monitoreo | `/monitoreo/...` | Petición del navegador | JSON de la API |

## Ejecución

```bash
docker compose up --build monitoreo
curl http://localhost:5002/monitoreo/evaluar/1
```
