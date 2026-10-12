# Servicio 3: Simulador

## Resumen

Proceso en Python (sin API) que genera lecturas aleatorias de temperatura y humedad para los sensores activos del catálogo y las envía periódicamente al servicio Mediciones.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `simulador/app.py` |
| Puerto | — (no expone API) |
| Contenedor Compose | `simulador` |
| Base de datos | — |

## Funcionamiento

1. Espera a que Mediciones responda `GET /health` (hasta 20 intentos, 2 s entre ellos).
2. Cada `INTERVALO_SEGUNDOS`, consulta `GET /sensores?activo=true` en Sensores.
3. Si Sensores no responde o devuelve una lista vacía, usa un catálogo de respaldo (3 sensores).
4. Por cada sensor genera un valor y lo envía con `POST /mediciones`.

| Tipo | Rango simulado | Unidad |
|---|---|---|
| temperatura | 15 – 40 | `C` |
| humedad | 20 – 100 | `%` |

## Variables de entorno

| Variable | Descripción | Valor en Compose |
|---|---|---|
| `MEDICIONES_URL` | URL del servicio Mediciones | `http://mediciones:5001` |
| `SENSORES_URL` | URL del servicio Sensores | `http://sensores:5003` |
| `INTERVALO_SEGUNDOS` | Segundos entre envíos | `5` |

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Simulador | Mediciones | `GET /health` | — | `{"status":"ok"}` |
| Simulador | Sensores | `GET /sensores?activo=true` | filtro `activo` | Lista de sensores activos |
| Simulador | Mediciones | `POST /mediciones` | `sensor_id`, `valor`, `unidad` | `201` con la medición creada |

## Ejecución

```bash
docker compose up --build simulador
docker compose logs -f simulador
```
