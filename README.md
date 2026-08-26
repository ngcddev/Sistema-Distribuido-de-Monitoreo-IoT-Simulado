# Arquitectura del Sistema: Sistema Distribuido de Monitoreo IoT Simulado

## Problema que resuelve
...

## Servicios del sistema
-
-
-

## Comunicación entre servicios
...

## Tipo de arquitectura
...

## Base de datos

- Motor: se usa **PostgreSQL 16** por ser un motor relacional, adecuado dado que los datos tienen una estructura fija y relaciones claras entre dispositivos, lectura y alerta.

Modelo de datos:

- **devices**: id (PK), nombre, tipo_sensor, ubicacion, activo (booleano), creado_en (timestamp)
- **readings**: id (PK), device_id (FK → devices), tipo, valor (numeric), timestamp — índice compuesto en (device_id, timestamp) para acelerar las consultas de histórico por dispositivo y rango de fechas
- **alerts**: id (PK), reading_id (FK → readings), regla, estado, creado_en (timestamp)

Las lecturas crecen sin límite en el tiempo, por lo que a futuro se evaluará particionado o purga por antigüedad.

## Usuarios del sistema

- **Administrador**: da de alta y de baja dispositivos, configura los umbrales de alerta, tiene acceso total al sistema.
- **Operador**: solo lectura del dashboard, histórico de lecturas y reconocimiento de alertas; no puede modificar dispositivos ni umbrales.
- **Servicio externo (integración)**: consume alertas vía webhook con token de API, sin acceso al resto del sistema.

## Riesgos y fallas posibles

- **Caída de la base de datos**: si Postgres cae, el servicio de ingesta debe reintentar o encolar las lecturas en vez de perderlas.
- **Escrituras concurrentes / datos duplicados**: se mitiga con constraint único o upsert idempotente al insertar lecturas.
- **Pico de carga del simulador**: puede saturar la ingesta; se mitiga con límite de tasa (rate limiting) o backpressure.
- **Falla de red entre frontend y backend**: el dashboard debe mostrar la última data conocida en vez de romperse.
- **Riesgo de proyecto**: si no se define el broker de mensajería antes de avanzar con los demás servicios, el resto del equipo queda bloqueado para implementar comunicación asíncrona.