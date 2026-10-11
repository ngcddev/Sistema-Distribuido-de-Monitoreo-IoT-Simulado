# Servicio 1: Mediciones

## Resumen

Servicio HTTP responsable de recibir y consultar las mediciones generadas por los sensores o por el simulador.

## Responsabilidades

- Verificar la disponibilidad del servicio.
- Registrar mediciones con sensor, valor y timestamp.
- Consultar todas las mediciones.
- Filtrar mediciones por `sensor_id`.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `mediciones/app.py` |
| Framework | Flask |
| Puerto | `5001` |
| Contenedor Compose | `mediciones` |
| Almacenamiento actual | Memoria del proceso |

## Ejecución local

```bash
python mediciones/app.py
```

El servicio queda disponible en `http://localhost:5001`.

## API

### `GET /health`

Comprueba que el servicio está disponible.

**Respuesta `200`:**

```json
{"status": "ok"}
```

### `POST /mediciones`

Registra una medición. Los campos `sensor_id` y `valor` son obligatorios. El campo `unidad` puede enviarse, aunque actualmente no se conserva en la respuesta almacenada.

**Solicitud:**

```json
{
  "sensor_id": 1,
  "valor": 27.5,
  "unidad": "C"
}
```

**Respuesta `201`:**

```json
{
  "sensor_id": 1,
  "valor": 27.5,
  "timestamp": "2026-09-07T00:00:00+00:00"
}
```

Si falta un campo obligatorio, responde con `400`.

### `GET /mediciones`

Devuelve todas las mediciones almacenadas.

### `GET /mediciones?sensor_id=1`

Devuelve únicamente las mediciones cuyo identificador coincide con el parámetro recibido.

## Integración

- El Simulador registra datos mediante `POST /mediciones`.
- Monitoreo consulta datos mediante `GET /mediciones?sensor_id=<id>`.

## Estado y pendientes

Actualmente los datos se almacenan en la lista `mediciones_db` y se pierden al detener el proceso. Queda pendiente incorporar persistencia en una base de datos y validar la existencia del sensor antes de registrar una medición.
