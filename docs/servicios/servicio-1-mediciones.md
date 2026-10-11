# Servicio 1: Mediciones

## Resumen

Servicio HTTP responsable de recibir y consultar las mediciones generadas por los
sensores o por el simulador. Persiste las lecturas en MySQL; es el único servicio
que se conecta a la base de datos.

## Responsabilidades

- Verificar la disponibilidad del servicio.
- Registrar mediciones con sensor, valor, unidad y timestamp.
- Consultar todas las mediciones.
- Filtrar mediciones por `sensor_id`.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `mediciones/app.py`, `mediciones/database.py` |
| Framework | Flask |
| Puerto | `5001` |
| Contenedor Compose | `mediciones` |
| Base de datos | MySQL 8 (servicio `mysql` en Compose) |
| Tabla | `mediciones` (script `mediciones/init.sql`) |
| Almacenamiento | Volumen `mysql_data` (`docker compose down` no borra los datos; `down -v` sí) |

## Variables de entorno

Compose inyecta en Mediciones: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y
`DB_NAME`. La plantilla está en `.env.example` (no subir el `.env` real).

Con `DB_USER=root`, `DB_PASSWORD` debe ser igual a `MYSQL_ROOT_PASSWORD`.

MySQL se publica en el host en el puerto `3307` (el contenedor usa `3306`).

## Ejecución

Con el sistema completo:

```bash
docker compose up --build
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

Registra una medición. Los campos `sensor_id` y `valor` son obligatorios. El campo
`unidad` es opcional y sí se almacena. El `timestamp` lo genera el servicio en
ISO 8601.

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
  "unidad": "C",
  "timestamp": "2026-09-07T00:00:00+00:00"
}
```

Si falta un campo obligatorio, responde con `400`. Si MySQL no está disponible,
responde con `503`.

### `GET /mediciones`

Devuelve todas las mediciones almacenadas en MySQL.

### `GET /mediciones?sensor_id=1`

Devuelve únicamente las mediciones cuyo `sensor_id` coincide con el parámetro.

### `GET /mediciones/<sensor_id>`

Igual que el filtro por query, usando el identificador en la ruta.

## Integración

- El Simulador registra datos mediante `POST /mediciones`.
- Monitoreo consulta datos mediante `GET /mediciones?sensor_id=<id>` (no se conecta a MySQL).

## Estado y pendientes

Persistencia en MySQL implementada. Queda pendiente validar la existencia del
sensor en un catálogo (si más adelante hay servicio de Sensores).
