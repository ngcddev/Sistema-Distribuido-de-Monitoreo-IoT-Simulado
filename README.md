<<<<<<< Updated upstream
# Sistema-Distribuido-de-Monitoreo-IoT-Simulado-
=======
# Arquitectura del Sistema: AgroSense

## Problema que resuelve
En las zonas rurales o alejadas con un dificil acceso limitado a energía eléctrica e internet, es difícil 
realizar un monitoreo constante de variables ambientales como lo son la temperatura, humedad, calidad del agua, estado del suelo y la calidad del aire. Por la falta de datos digitalizados y actualizados 
dificulta la toma de decisiones en actividades como la agricultura, la investigación ambiental y el cuidado de los recursos naturales.

El sistema resuelve esto mediante una red de sensores IoT simulada que recolecta, transmite y centraliza datos ambientales, facilitando su consulta, análisis y la generación de alertas cuando los valores salen de los rangos normales.

## Servicios del sistema
-
-
-

## Comunicación entre servicios
Los servicios del sistema se encuentran conectados entre sí para intercambiar información y realizar sus funciones de manera coordinada. Cada servicio cumple una función específica y se comunica con los demás cuando necesita datos o cuando ocurre algún evento.

-. El Servicio de Monitoreo recibe los datos generados por el Servicio de Simulación IoT para procesarlos y analizar el estado de las variables monitoreadas.
-. El Servicio de Notificaciones recibe eventos del Servicio de Monitoreo cuando se detecta que algún valor está fuera de los rangos establecidos.
-. El Servicio de Simulación IoT responde proporcionando los datos simulados de los sensores al Servicio de Monitoreo.
-. El Servicio de Monitoreo genera eventos de alerta cuando detecta condiciones anormales, y el Servicio de Notificaciones procesa estos eventos y genera la notificación correspondiente.

Monitoreo → recibe datos → Simulación IoT
Simulación IoT → proporciona datos → Monitoreo
Monitoreo → genera alerta → Notificaciones
Notificaciones → procesa alerta → genera notificación

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
>>>>>>> Stashed changes
