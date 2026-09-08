# Servicio 2: Monitoreo

## Resumen

Servicio HTTP que consulta las mediciones de un sensor y genera un resumen con su cantidad de lecturas, promedio y medición más reciente.

## Responsabilidades

- Verificar la disponibilidad del servicio.
- Consultar el servicio de Mediciones.
- Calcular el promedio de los valores recibidos.
- Identificar la lectura más reciente.
- Devolver respuestas controladas cuando Mediciones no está disponible.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `monitoreo/app.py` |
| Framework | Flask |
| Puerto | `5002` |
| Contenedor Compose | `monitoreo` |
| Dependencia | Servicio de Mediciones |

## Configuración

`MEDICIONES_URL` define la dirección base del servicio de Mediciones.

**Docker Compose:**

```text
MEDICIONES_URL=http://mediciones:5001
```

**Ejecución local recomendada:**

```text
MEDICIONES_URL=http://localhost:5001
```

Para ejecutar el servicio localmente:

```bash
python monitoreo/app.py
```

## API

### `GET /health`

Comprueba que el servicio está disponible.

**Respuesta `200`:**

```json
{"status": "ok"}
```

### `GET /monitoreo/<sensor_id>`

Consulta `GET /mediciones?sensor_id=<sensor_id>` y devuelve un resumen.

**Respuesta con lecturas:**

```json
{
  "sensor_id": "1",
  "cantidad_lecturas": 2,
  "promedio": 26.75,
  "ultima_lectura": {
    "sensor_id": "1",
    "valor": 27.5,
    "timestamp": "2026-09-07T00:00:00+00:00"
  }
}
```

Cuando no hay lecturas, responde `200` con `cantidad_lecturas` igual a `0` y los campos `promedio` y `ultima_lectura` en `null`.

Si Mediciones no responde, se agota el tiempo de espera o devuelve un estado distinto de `200`, Monitoreo responde con `503`.

## Reglas de cálculo

- `cantidad_lecturas`: número de lecturas recibidas.
- `promedio`: media aritmética de `valor`, redondeada a dos decimales.
- `ultima_lectura`: lectura cuyo `timestamp` sea más reciente.

## Estado y pendientes

El servicio calcula resúmenes, pero todavía no implementa reglas de alerta ni persistencia propia. La configuración predeterminada del código agrega `/mediciones` a `MEDICIONES_URL`; por eso, al ejecutar localmente debe definirse la variable con la URL base indicada arriba para evitar duplicar la ruta.
