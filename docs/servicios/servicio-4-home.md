# Servicio 4: Home

## Resumen

Interfaz web (HTML, CSS y JavaScript) servida por Nginx. Es el punto de entrada del usuario: desde el navegador permite consultar y administrar el catálogo de sensores, administrar mediciones y consultar el análisis de Monitoreo. Nginx también actúa como **proxy inverso**: reenvía `/sensores`, `/mediciones` y `/monitoreo` al **API Gateway** (`http://gateway:8000`), que las enruta a su microservicio, por lo que el navegador solo habla con el puerto de Home.

Home no tiene base de datos ni lógica de negocio.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `home/` |
| Tipo | Frontend estático + proxy (Nginx) |
| Puerto | `8080` en el host → `80` en el contenedor |
| Contenedor Compose | `home` |
| Base de datos | — |

## Estructura

| Archivo | Función |
|---|---|
| `index.html` | Estructura del dashboard y sus tres vistas |
| `style.css` | Estilos |
| `script.js` | Llamadas a las APIs, renderizado de resultados y gráfico |
| `nginx.conf` | Sirve los estáticos y reenvía `/sensores`, `/mediciones` y `/monitoreo` al API Gateway |
| `Dockerfile` | Imagen `nginx:alpine` con la configuración y los estáticos |

La gráfica usa Chart.js, cargada desde un CDN; si el navegador no tiene conexión, el resto de la interfaz funciona y solo se omite el gráfico.

## Vistas

| Vista | Qué permite |
|---|---|
| Vista general | Resumen global, métricas y evaluación de un sensor, ver umbrales y alertas, y gráfico de sus últimas 10 lecturas |
| Sensores | Tabla del catálogo (`GET /sensores`) con filtros por tipo y estado, alta (`POST`), activar/desactivar (`PUT`) y baja (`DELETE`) |
| Administración de mediciones | GET total, GET por id, POST, PUT, PATCH y DELETE sobre mediciones |

## Proxy (Nginx)

| Ruta en Home | Destino interno |
|---|---|
| `/` | Archivos estáticos (`index.html`) |
| `/sensores` | `http://gateway:8000` (Gateway → Sensores) |
| `/mediciones` | `http://gateway:8000` (Gateway → Mediciones) |
| `/monitoreo` | `http://gateway:8000` (Gateway → Monitoreo) |

El navegador nunca llama a un microservicio directamente: todo pasa por Nginx → Gateway.

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Home (navegador) | Sensores | `GET /sensores`, `GET /sensores?tipo=X&activo=true\|false` | filtros opcionales | Lista de sensores en JSON |
| Home (navegador) | Sensores | `POST /sensores`, `PUT /sensores/<id>`, `DELETE /sensores/<id>` | JSON con `nombre`, `tipo`, `ubicacion`, `activo` | Sensor creado o modificado, o confirmación |
| Home (navegador) | Mediciones | `GET /mediciones`, `GET /mediciones?sensor_id=X&limit=10`, `GET /mediciones/<id>` | filtros opcionales | Lista o medición en JSON |
| Home (navegador) | Mediciones | `POST` / `PUT` / `PATCH` / `DELETE /mediciones[/<id>]` | JSON con `sensor_id`, `valor`, `unidad` | Medición creada, modificada o confirmación |
| Home (navegador) | Monitoreo | `GET /monitoreo/resumen-general` | — | Total de lecturas, sensores y promedio global |
| Home (navegador) | Monitoreo | `GET /monitoreo/<sensor_id>` | id del sensor | Cantidad, promedio y última lectura |
| Home (navegador) | Monitoreo | `GET /monitoreo/evaluar/<sensor_id>` | id del sensor | Evaluación contra el umbral (registra alerta si aplica) |
| Home (navegador) | Monitoreo | `GET /monitoreo/umbrales`, `GET /monitoreo/alertas?limit=10` | — | Lista en JSON |

## Variables de entorno

Home no usa variables de entorno: las rutas del proxy están fijas en `nginx.conf` con los nombres de servicio de Compose.

## Ejecución

Home depende del API Gateway (y este de Sensores, Mediciones y Monitoreo); conviene levantarlo con todo el sistema:

```bash
docker compose up -d --build
```

Luego abrir <http://localhost:8080>; el catálogo está en **Sensores**, en el menú lateral.
