# Servicio Sensores

## Resumen

API REST (Flask) que administra el catálogo de sensores: nombre, tipo, ubicación y estado activo. Es la fuente de verdad que consultan el Simulador (qué sensores generar) y Monitoreo (de qué tipo es cada sensor). Persiste en MySQL.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `sensores/app.py`, `sensores/database.py` |
| Framework | Flask |
| Puerto | `5003` |
| Contenedor Compose | `sensores` |
| Base de datos | `sensores` en el contenedor `mysql_sensores` |

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|---|---|---|---|
| GET | `/health` | Comprueba el servicio y la conexión a la BD | `200`, `503` |
| GET | `/sensores` | Lista sensores. Filtros: `tipo`, `activo` (`true` o `false`) | `200`, `400` |
| GET | `/sensores/<id>` | Obtiene un sensor | `200`, `404` |
| POST | `/sensores` | Crea un sensor (`nombre`, `tipo` obligatorios; `ubicacion`, `activo` opcionales) | `201`, `400` |
| PUT | `/sensores/<id>` | Reemplaza un sensor | `200`, `400`, `404` |
| DELETE | `/sensores/<id>` | Elimina un sensor | `200`, `404` |

Validaciones: `nombre` de 1 a 80 caracteres, `tipo` ∈ {`temperatura`, `humedad`}, `ubicacion` de hasta 80 caracteres y `activo` booleano.

## Base de datos

| Base | Tabla | Columnas |
|---|---|---|
| `sensores` | `sensores` | `id` (PK), `nombre` VARCHAR(80), `tipo` VARCHAR(30), `ubicacion` VARCHAR(80), `activo` TINYINT(1) por defecto 1 |

Si la tabla está vacía se cargan tres sensores: 1 *Temperatura sala*, 2 *Temperatura cocina* y 3 *Humedad invernadero*. Script de referencia: [`bases_datos/sensores.sql`](../../bases_datos/sensores.sql).

## Variables de entorno

| Variable | Descripción | Valor en Compose |
|---|---|---|
| `DB_HOST` | Host de MySQL | `mysql_sensores` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `DB_USER` | Usuario de MySQL (necesita `CREATE`) | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `root` |
| `DB_NAME` | Nombre de la base | `sensores` |

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Simulador | Sensores | `GET /sensores?activo=true` | filtro `activo` | Lista de sensores activos |
| Monitoreo | Sensores | `GET /sensores/<id>` | `id` del sensor | Sensor con su `tipo` |

## Ejecución

```bash
docker compose up --build sensores
curl http://localhost:5003/sensores
```
