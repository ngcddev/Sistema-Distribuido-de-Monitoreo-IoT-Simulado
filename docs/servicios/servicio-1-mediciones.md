# Servicio 1: Mediciones

## Resumen

API REST (Flask) que recibe, almacena, consulta, modifica y elimina las lecturas generadas por el Simulador o por sensores. Persiste en MySQL.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `mediciones/app.py`, `mediciones/database.py` |
| Framework | Flask |
| Puerto | `5001` |
| Contenedor Compose | `mediciones` |
| Base de datos | `mediciones` en el contenedor `mysql_mediciones` |

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|---|---|---|---|
| GET | `/health` | Comprueba el servicio y la conexión a la BD | `200`, `503` |
| POST | `/mediciones` | Registra una medición (`sensor_id`, `valor` obligatorios; `unidad` opcional) | `201`, `400` |
| GET | `/mediciones` | Lista mediciones en orden cronológico. Filtros: `sensor_id`, `id`, `limit` (las N más recientes, máx. 1000) | `200`, `400` |
| GET | `/mediciones/<id>` | Obtiene una medición por identificador | `200`, `404` |
| GET | `/mediciones/sensor/<sensor_id>` | Lista las mediciones de un sensor | `200` |
| PUT | `/mediciones/<id>` | Reemplaza `sensor_id`, `valor` y `unidad` | `200`, `400`, `404` |
| PATCH | `/mediciones/<id>` | Actualiza `valor` y/o `unidad` | `200`, `400`, `404` |
| DELETE | `/mediciones/<id>` | Elimina una medición | `200`, `404` |

Validaciones: `valor` debe ser numérico (no booleano), `sensor_id` entero o texto de 1 a 50 caracteres y `unidad` texto de máximo 10 caracteres. El `timestamp` lo asigna el servicio (UTC, ISO 8601). Si la BD no está disponible responde `503`.

**Ejemplo `POST /mediciones`:**

```json
{"sensor_id": 1, "valor": 27.5, "unidad": "C"}
```

```json
{"id": 1, "sensor_id": "1", "valor": 27.5, "unidad": "C", "timestamp": "2026-10-11T15:00:00+00:00"}
```

## Cambio de contrato

`GET /mediciones/sensor/<sensor_id>` **reemplaza** a `GET /mediciones/<sensor_id>`. La ruta `GET /mediciones/<id>` ahora solo acepta un identificador entero de medición.

## Base de datos

| Base | Tabla | Columnas |
|---|---|---|
| `mediciones` | `mediciones` | `id` (PK, autoincremental), `sensor_id` VARCHAR(50) con índice, `valor` DOUBLE, `unidad` VARCHAR(10), `timestamp` VARCHAR(40) |

Script de referencia: [`bases_datos/mediciones.sql`](../../bases_datos/mediciones.sql). El servicio crea la base y la tabla al arrancar.

## Variables de entorno

| Variable | Descripción | Valor en Compose |
|---|---|---|
| `DB_HOST` | Host de MySQL | `mysql_mediciones` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `DB_USER` | Usuario de MySQL (necesita `CREATE`) | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `root` |
| `DB_NAME` | Nombre de la base | `mediciones` |

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Simulador | Mediciones | `GET /health` | — | `{"status":"ok"}` |
| Simulador | Mediciones | `POST /mediciones` | `sensor_id`, `valor`, `unidad` | `201` con la medición creada |
| Monitoreo | Mediciones | `GET /mediciones?sensor_id=X&limit=N` | `sensor_id`, `limit` | Lista de mediciones |
| Home (Nginx) | Mediciones | `/mediciones/...` | Petición del navegador | JSON de la API |

## Ejecución

```bash
docker compose up --build mediciones
curl http://localhost:5001/health
```
