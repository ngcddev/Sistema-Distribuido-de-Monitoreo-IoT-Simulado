# Sistema Distribuido de Monitoreo IoT Simulado

Sistema distribuido para generar, registrar y consultar mediciones ambientales sin depender de hardware físico. El proyecto utiliza microservicios independientes que se comunican mediante HTTP/REST.

## Estado actual

En este avance están implementados los siguientes componentes:

| Componente | Responsabilidad | Estado |
|---|---|---|
| Mediciones | Recibe y consulta lecturas | Implementado |
| Monitoreo | Calcula resúmenes por sensor | Implementado |
| Simulador | Genera y envía lecturas periódicamente | Implementado como proceso local |
| Sensores | Catálogo de sensores | Pendiente de integración en esta rama |
| Home | Interfaz principal | Pendiente |

Las mediciones se almacenan temporalmente en memoria. Al reiniciar el servicio de Mediciones, los datos se pierden.

## Estructura del proyecto

```text
.
├── docs/
│   ├── ARCHITECTURE.md
│   └── servicios/
│       ├── servicio-1-mediciones.md
│       ├── servicio-2-monitoreo.md
│       └── servicio-3-simulador.md
├── mediciones/
│   ├── app.py
│   └── requirements.txt
├── monitoreo/
│   ├── app.py
│   └── requirements.txt
├── simulador/
│   ├── app.py
│   └── requirements.txt
├── compose.yml
├── docker-compose.yml
└── README.md
```

## Servicios

### Mediciones

Expone el servicio en el puerto `5001`.

- `GET /health`: comprueba disponibilidad.
- `POST /mediciones`: registra una medición.
- `GET /mediciones`: consulta todas las mediciones.
- `GET /mediciones?sensor_id=<id>`: filtra por sensor.

Documentación: [docs/servicios/servicio-1-mediciones.md](docs/servicios/servicio-1-mediciones.md)

### Monitoreo

Expone el servicio en el puerto `5002` y consulta Mediciones para generar resúmenes.

- `GET /health`: comprueba disponibilidad.
- `GET /monitoreo/<sensor_id>`: devuelve cantidad, promedio y última lectura.

Documentación: [docs/servicios/servicio-2-monitoreo.md](docs/servicios/servicio-2-monitoreo.md)

### Simulador

Es un proceso de fondo que genera valores aleatorios de temperatura y humedad cada cinco segundos y los envía a Mediciones. Consulta el catálogo de Sensores antes de iniciar el envío.

Documentación: [docs/servicios/servicio-3-simulador.md](docs/servicios/servicio-3-simulador.md)

## Comunicación

```text
Simulador --POST /mediciones--> Mediciones
Monitoreo --GET /mediciones--> Mediciones
Simulador --GET /sensores------> Sensores (pendiente de integración)
```

## Ejecución local

Instala las dependencias de cada servicio:

```bash
pip install -r mediciones/requirements.txt
pip install -r monitoreo/requirements.txt
pip install -r simulador/requirements.txt
```

En terminales separadas, inicia Mediciones y Monitoreo:

```bash
python mediciones/app.py
python monitoreo/app.py
```

El Simulador requiere que el servicio de Sensores esté disponible. Cuando Sensores se integre en la rama actual, podrá ejecutarse con:

```bash
python simulador/app.py
```

## Docker Compose

El archivo `docker-compose.yml` actual levanta Mediciones y Monitoreo:

```bash
docker compose -f docker-compose.yml up --build
```

`compose.yml` permanece reservado para la configuración distribuida que se definirá en un avance posterior.

## Decisiones y pendientes

- Se utiliza Flask para los servicios HTTP.
- La comunicación entre servicios se realiza mediante HTTP/REST.
- Las lecturas se almacenan en memoria durante este avance.
- La integración de Sensores y Simulador en Docker Compose está pendiente.
- La interfaz Home está pendiente.
- La persistencia en PostgreSQL, las alertas y la autenticación quedan para avances posteriores.

## Documentación adicional

- [Arquitectura del sistema](docs/ARCHITECTURE.md)
- [Servicio de Mediciones](docs/servicios/servicio-1-mediciones.md)
- [Servicio de Monitoreo](docs/servicios/servicio-2-monitoreo.md)
- [Servicio Simulador](docs/servicios/servicio-3-simulador.md)
