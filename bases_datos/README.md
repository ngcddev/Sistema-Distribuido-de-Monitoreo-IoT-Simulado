# Bases de datos

Cada servicio con persistencia tiene su propia base MySQL 8.0 (un contenedor y un
volumen por servicio). Los scripts de esta carpeta son **de referencia**: los servicios
crean su base y sus tablas por sí solos al arrancar (`inicializar()` en cada
`database.py`), reintentando mientras MySQL queda disponible. Esto requiere un usuario
con permiso `CREATE`; por defecto se usa `root`.

| Archivo | Servicio | Base de datos | Tablas |
|---|---|---|---|
| `mediciones.sql` | Mediciones | `mediciones` | `mediciones` |
| `sensores.sql` | Sensores | `sensores` | `sensores` |
| `monitoreo.sql` | Monitoreo | `monitoreo` | `umbrales`, `alertas` |

## Microservicios, bases de datos y operaciones

Las operaciones son las que expone cada servicio (las mismas rutas a través del API Gateway,
`http://localhost:8000`). Detalle de cada endpoint en [docs/endpoints/README.md](../docs/endpoints/README.md).

| Microservicio | Base de datos | Tablas principales | Operaciones implementadas |
|---|---|---|---|
| Sensores | `sensores` (contenedor `mysql_sensores`, volumen `mysql_sensores_data`) | `sensores` | **Crear:** `POST /sensores` · **Listar:** `GET /sensores` (filtros `tipo`, `activo`) · **Consultar:** `GET /sensores/<id>` · **Actualizar:** `PUT /sensores/<id>` · **Eliminar:** `DELETE /sensores/<id>` |
| Mediciones | `mediciones` (contenedor `mysql_mediciones`, volumen `mysql_mediciones_data`) | `mediciones` | **Crear:** `POST /mediciones` · **Listar:** `GET /mediciones` (filtros `sensor_id`, `id`, `limit`) · **Consultar:** `GET /mediciones/<id>`, `GET /mediciones/sensor/<sensor_id>` · **Actualizar:** `PUT /mediciones/<id>` (completo), `PATCH /mediciones/<id>` (parcial) · **Eliminar:** `DELETE /mediciones/<id>` |
| Monitoreo (umbrales) | `monitoreo` (contenedor `mysql_monitoreo`, volumen `mysql_monitoreo_data`) | `umbrales` | **Crear:** `POST /monitoreo/umbrales` (`409` si ya existe uno para el tipo) · **Listar:** `GET /monitoreo/umbrales` · **Consultar:** `GET /monitoreo/umbrales/<id>` · **Actualizar:** `PUT /monitoreo/umbrales/<id>` · **Eliminar:** `DELETE /monitoreo/umbrales/<id>` |
| Monitoreo (alertas) | `monitoreo` (misma base que umbrales) | `alertas` | **Crear:** automática al evaluar con `GET /monitoreo/evaluar/<sensor_id>` cuando la lectura sale del umbral (`INSERT IGNORE`: una alerta por medición) · **Listar:** `GET /monitoreo/alertas` (filtros `sensor_id`, `limit`) · **Consultar:** `GET /monitoreo/alertas/<id>` · **Eliminar:** `DELETE /monitoreo/alertas/<id>` · *Sin PUT: una alerta es un registro histórico y no se edita a mano.* |

Ningún servicio lee ni escribe la base de otro: Monitoreo obtiene las lecturas con `GET /mediciones`
y el tipo de cada sensor con `GET /sensores/<id>`, nunca por SQL.

## Estructura de las tablas

| Tabla | Columnas | Claves e índices | Datos iniciales |
|---|---|---|---|
| `sensores.sensores` | `id`, `nombre`, `tipo`, `ubicacion`, `activo` | PK `id` | 3 sensores (2 de temperatura, 1 de humedad) |
| `mediciones.mediciones` | `id`, `sensor_id`, `valor`, `unidad`, `timestamp` | PK `id`, índice `idx_sensor (sensor_id)` | — (las crea el Simulador) |
| `monitoreo.umbrales` | `id`, `tipo`, `minimo`, `maximo`, `unidad` | PK `id`, `UNIQUE (tipo)` | temperatura 10–35 °C, humedad 30–80 % |
| `monitoreo.alertas` | `id`, `medicion_id`, `sensor_id`, `tipo`, `valor`, `estado`, `detalle`, `timestamp` | PK `id`, `UNIQUE (medicion_id)`, índice `idx_sensor (sensor_id)` | — (las genera la evaluación) |

## Persistencia

Los datos viven en los volúmenes con nombre, no en los contenedores: se pueden detener o recrear los
servicios (`docker compose rm -sf ...` y `docker compose up -d`) sin perder información. Solo
`docker compose down -v` borra los volúmenes. Prueba automatizada:
`bash docs/pruebas/pruebas-integrales.sh persistencia`.
