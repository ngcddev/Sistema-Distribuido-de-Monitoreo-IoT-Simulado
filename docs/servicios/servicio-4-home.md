# Servicio 4: Home

## Resumen

Interfaz web (HTML, CSS y JavaScript) servida por Nginx. Es el punto de entrada del usuario: desde el navegador permite administrar mediciones y consultar el análisis de Monitoreo. Nginx también actúa como **proxy inverso**: reenvía `/mediciones` y `/monitoreo` a sus APIs, por lo que el navegador solo habla con el puerto de Home.

Home no tiene base de datos ni lógica de negocio.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `home/` |
| Tipo | Frontend estático + proxy (Nginx) |
| Puerto | `8080` en el host → `8080` en el contenedor (imagen sin privilegios) |
| Contenedor Compose | `home` |
| Base de datos | — |

## Estructura

| Archivo | Función |
|---|---|
| `index.html` | Estructura del dashboard y sus dos vistas |
| `style.css` | Estilos: variables de color en `:root`, clases de estado (`.estado-*`) y sin estilos en línea |
| `script.js` | Llamadas a las APIs, renderizado de resultados (como texto, nunca como HTML) y gráfico |
| `nginx.conf` | Sirve los estáticos y define el proxy hacia Mediciones y Monitoreo (resuelve los servicios con el DNS de Docker en cada petición, así arranca aunque un servicio aún no exista) |
| `docker-entrypoint.d/15-credenciales.sh` | Se ejecuta al arrancar el contenedor: genera `/tmp/credenciales.conf` con las credenciales de administración que Nginx exige para escribir |
| `proxy_params.conf` | Cabeceras y tiempos de espera comunes del proxy |
| `favicon.svg` | Icono de la pestaña |
| `e2e/` | Pruebas de navegador (ver README, "Integración continua") |
| `vendor/chart.umd.min.js` | Chart.js 4.4.1 (MIT) servido localmente, sin CDN. Cómo actualizarlo: `vendor/README.md` |
| `Dockerfile` | Imagen `nginxinc/nginx-unprivileged:1.28-alpine` (no corre como root) con la configuración y los estáticos |

La gráfica usa Chart.js incluido en `home/vendor/`, así que funciona sin conexión a internet. Se refresca sola cada 10 s mientras se vea la vista general.

La vista activa vive en la URL: `#general` (por defecto) y `#administracion`; el enlace activo lleva `aria-current="page"`. El botón DELETE pide confirmación y los mensajes de estado son regiones `aria-live` para lectores de pantalla.

### Accesibilidad y buenas prácticas

- Cada vista tiene un único `h1` y los encabezados no saltan de nivel.
- Los datos de las APIs se muestran con `textContent`: aunque un valor contenga HTML, se ve como texto y no se ejecuta.
- La página declara `description`, `theme-color` y `color-scheme`, y los campos llevan `name` y `autocomplete`.
- Hay foco visible en enlaces, botones y campos, y los botones secundarios cambian al pasar el cursor.
- Los scripts se cargan con `defer`.

## Vistas

| Vista | Qué permite |
|---|---|
| Vista general | Resumen global, métricas y evaluación de un sensor, ver umbrales y alertas, y gráfico de sus últimas 10 lecturas |
| Administración de mediciones | GET total, GET por id, POST, PUT, PATCH y DELETE sobre mediciones |

## Proxy (Nginx)

| Ruta en Home | Destino interno |
|---|---|
| `/` | Archivos estáticos (`index.html`) |
| `/mediciones` | `http://mediciones:5001` |
| `/monitoreo` | `http://monitoreo:5002` |

Sensores no se expone por Home: el navegador no lo consulta directamente.

Las rutas del proxy solo coinciden con `/mediciones` y `/monitoreo` (y sus subrutas), no con prefijos como `/medicionesXYZ`.

### Acceso: quién puede escribir

Nginx permite **consultar** libremente, pero **crear, modificar y borrar** (`POST`, `PUT`, `PATCH`, `DELETE` sobre `/mediciones` y `/monitoreo`) exige el usuario y la contraseña de `HOME_ADMIN_USER` / `HOME_ADMIN_PASSWORD`. Sin ellas responde `401` con el desafío Basic (el navegador muestra su diálogo de acceso) y un JSON con el motivo; la pantalla de administración lo muestra como mensaje de error. `POST /monitoreo/evaluar/*` queda libre porque es idempotente.

Al arrancar, `15-credenciales.sh` convierte las dos variables en la cabecera `Authorization` esperada y la guarda en `/tmp/credenciales.conf`; `nginx.conf` la incluye y decide con dos `map` (¿escribe?, ¿credenciales correctas?). Las credenciales no se reenvían a las APIs. Limitaciones: autenticación Basic sobre HTTP (usuario y contraseña viajan sin cifrar; para exponerlo hace falta HTTPS) y una sola cuenta.

### Seguridad

Nginx añade `Content-Security-Policy` (solo recursos propios, sin scripts ni estilos en línea: la interfaz usa clases de `style.css`), `X-Content-Type-Options`, `X-Frame-Options: DENY` y `Referrer-Policy`, oculta la versión del servidor, comprime con gzip y hace que el navegador revalide los estáticos en cada carga.

## Comunicación

| Solicita | Responde | Endpoint | Enviado | Recibido |
|---|---|---|---|---|
| Home (navegador) | Mediciones | `GET /mediciones?limit=8`, `GET /mediciones?sensor_id=X&limit=10`, `GET /mediciones/<id>`, `GET /mediciones/estadisticas` | filtros opcionales | Lista, medición o totales en JSON |
| Home (navegador) | Mediciones | `POST` / `PUT` / `PATCH` / `DELETE /mediciones[/<id>]` | JSON con `sensor_id`, `valor`, `unidad` | Medición creada, modificada o confirmación |
| Home (navegador) | Monitoreo | `GET /monitoreo/resumen-general` | — | Total de lecturas, sensores y promedio por unidad |
| Home (navegador) | Monitoreo | `GET /monitoreo/<sensor_id>` | id del sensor | Cantidad, promedio y última lectura |
| Home (navegador) | Monitoreo | `POST /monitoreo/evaluar/<sensor_id>` | id del sensor | Evaluación contra el umbral (registra alerta si aplica) |
| Home (navegador) | Monitoreo | `GET /monitoreo/umbrales`, `GET /monitoreo/alertas?limit=10` | — | Lista en JSON |

## Variables de entorno

| Variable | Descripción | Valor |
|---|---|---|
| `HOME_ADMIN_USER` | Usuario que Nginx exige para escribir | obligatoria (`.env`) |
| `HOME_ADMIN_PASSWORD` | Contraseña de ese usuario | obligatoria (`.env`) |

Las rutas del proxy están fijas en `nginx.conf` con los nombres de servicio de Compose.

## Ejecución

Home espera (`depends_on: service_healthy`) a que Mediciones y Monitoreo estén saludables; conviene levantarlo con todo el sistema:

```bash
docker compose up --build
```

Luego abrir <http://localhost:8080>.
