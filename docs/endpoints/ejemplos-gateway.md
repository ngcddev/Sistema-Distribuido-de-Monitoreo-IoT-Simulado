# URLs para Postman

Los contenedores ya están corriendo (`docker compose up -d --build`). Todas las
peticiones pasan por el **API Gateway** en el puerto **8000**. En Postman elige el
método, pega la URL y, si es POST, PUT o PATCH, body en raw JSON.

> **Credenciales:** crear, modificar y borrar (POST, PUT, PATCH, DELETE) piden *Authorization → Basic Auth*
> con `HOME_ADMIN_USER` / `HOME_ADMIN_PASSWORD` del `.env`; sin ellas el Gateway responde `401`.
> Consultar y `POST /monitoreo/evaluar/<id>` no las piden.

## Gateway — health general

| Método | URL |
|---|---|
| GET | http://localhost:8000/health |

Devuelve el estado de los 3 servicios (`mediciones`, `monitoreo`, `sensores`).

## Sensores

| Método | URL |
|---|---|
| GET | http://localhost:8000/sensores |
| GET | http://localhost:8000/sensores?tipo=temperatura&activo=true |
| POST | http://localhost:8000/sensores |
| GET | http://localhost:8000/sensores/1 |
| PUT | http://localhost:8000/sensores/1 |
| DELETE | http://localhost:8000/sensores/1 |

POST y PUT:

```json
{"nombre": "Sensor demo", "tipo": "humedad", "ubicacion": "laboratorio", "activo": true}
```

`tipo` solo acepta `temperatura` o `humedad`.

## Mediciones

| Método | URL |
|---|---|
| GET | http://localhost:8000/mediciones |
| GET | http://localhost:8000/mediciones?sensor_id=1&limit=10 |
| POST | http://localhost:8000/mediciones |
| GET | http://localhost:8000/mediciones/1 |
| PUT | http://localhost:8000/mediciones/1 |
| PATCH | http://localhost:8000/mediciones/1 |
| DELETE | http://localhost:8000/mediciones/1 |
| GET | http://localhost:8000/mediciones/sensor/1 |

POST y PUT:

```json
{"sensor_id": 1, "valor": 22.5, "unidad": "C"}
```

PATCH:

```json
{"valor": 24}
```

Para generar una alerta, POST con `"valor": 50` (supera el umbral de temperatura).

## Monitoreo

Umbrales:

| Método | URL |
|---|---|
| GET | http://localhost:8000/monitoreo/umbrales |
| POST | http://localhost:8000/monitoreo/umbrales |
| GET | http://localhost:8000/monitoreo/umbrales/1 |
| PUT | http://localhost:8000/monitoreo/umbrales/1 |
| DELETE | http://localhost:8000/monitoreo/umbrales/1 |

Alertas:

| Método | URL |
|---|---|
| GET | http://localhost:8000/monitoreo/alertas |
| GET | http://localhost:8000/monitoreo/alertas?sensor_id=1&limit=10 |
| DELETE | http://localhost:8000/monitoreo/alertas/1 |

Análisis:

| Método | URL |
|---|---|
| GET | http://localhost:8000/monitoreo/resumen-general |
| GET | http://localhost:8000/monitoreo/evaluar/1 |
| GET | http://localhost:8000/monitoreo/1 |
| GET | http://localhost:8000/monitoreo/circuitos |

POST y PUT de umbral:

```json
{"tipo": "presion_demo", "minimo": 1, "maximo": 5, "unidad": "bar"}
```

`/monitoreo/circuitos` muestra el estado de los circuit breakers
(`closed` / `open` / `half_open`) de las llamadas a Mediciones y Sensores.

## Errores (para comprobar que responden JSON, no HTML)

| Método | URL | Esperado |
|---|---|---|
| GET | http://localhost:8000/no-existe | 404 JSON `{"error": ...}` |
| DELETE | http://localhost:8000/sensores | 405 JSON `{"error": ...}` |
| GET | http://localhost:8000/sensores/99999 | 404 JSON `{"error": "sensor no encontrado"}` |
| POST | http://localhost:8000/mediciones (body `{}`) | 400 JSON `{"error": "sensor_id y valor son requeridos"}` |

## Prueba de tolerancia a fallos

```bash
docker compose stop mediciones
# luego en Postman:
# GET http://localhost:8000/mediciones            -> 502 "servicio no disponible"
# GET http://localhost:8000/monitoreo/resumen-general -> 503
# GET http://localhost:8000/health                -> mediciones: "no disponible"
# GET http://localhost:8000/monitoreo/circuitos   -> estado open tras 3 fallos

docker compose start mediciones
# el circuito pasa a half_open y luego closed solo
```

Orden sugerido en la presentación: health del gateway, listar sensores, POST de una
medición en 22.5, `GET /monitoreo/1`, POST de una medicición en 50 y
`GET /monitoreo/evaluar/1` (debe responder `ALERTA_CRITICA`).
