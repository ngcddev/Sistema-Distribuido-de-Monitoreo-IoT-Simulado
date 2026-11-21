# Servicio API Gateway

## Resumen

Punto de entrada único hacia las APIs de Sensores, Mediciones y Monitoreo. **No tiene lógica de negocio ni
acceso a bases de datos**: identifica el servicio por el primer segmento de la ruta, reenvía método, parámetros,
cuerpo y devuelve la respuesta con su código de estado. Traduce los fallos de comunicación a errores HTTP claros.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `gateway/app.py` |
| Framework | Flask + gunicorn (2 workers), usuario sin privilegios |
| Puerto | `8000` (publicado) |
| Contenedor Compose | `gateway` |
| Base de datos | Ninguna |

## Rutas

| Ruta | Servicio destino |
|---|---|
| `/sensores...` | `SENSOR_SERVICE_URL` (`http://sensores:5003`) |
| `/mediciones...` | `MEDICIONES_SERVICE_URL` (`http://mediciones:5001`) |
| `/monitoreo...` | `MONITOREO_SERVICE_URL` (`http://monitoreo:5002`) |
| `GET /health` | El propio Gateway: consulta `/health` de cada servicio y devuelve su estado |
| `GET /` | Lista de rutas |

El Gateway reenvía cualquier subruta (`/mediciones/sensor/2`, `/monitoreo/umbrales/1`, ...), de modo que un
endpoint nuevo en un servicio queda accesible sin tocar el Gateway.

## Errores

| Situación | Código |
|---|---|
| Ruta que no corresponde a ningún servicio | `404` |
| Método no permitido | `405` |
| Servicio caído o sin conexión | `503` |
| Servicio que no responde en `GATEWAY_TIMEOUT` | `504` |
| Error interno del Gateway | `500` |

Todas las respuestas de error son JSON `{"error": "..."}`. Los errores del propio servicio destino (400, 404,
409, 5xx...) se reenvían tal cual.

## Variables de entorno

| Variable | Descripción | Por defecto |
|---|---|---|
| `SENSOR_SERVICE_URL`, `MEDICIONES_SERVICE_URL`, `MONITOREO_SERVICE_URL` | Direcciones internas | nombres de servicio de Compose |
| `GATEWAY_TIMEOUT` | Timeout (s) de cada solicitud reenviada; mayor que los de Monitoreo | `8` |

## Pruebas

`gateway/tests/test_gateway.py` (pytest, sin red): enrutamiento de cada servicio, reenvío de método/query/cuerpo,
conservación de códigos, 503, 504, 404, 405 y `/health`.
