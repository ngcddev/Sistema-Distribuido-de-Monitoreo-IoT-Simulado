# Pruebas del tercer avance

Todas las pruebas se ejecutan **sobre el stack real** (`docker compose up -d --build`) y **a través del API
Gateway** (`http://localhost:8000`). El script [pruebas-integrales.sh](pruebas-integrales.sh) las automatiza y
su salida completa está en [evidencia-ejecucion.txt](evidencia-ejecucion.txt) (cada línea muestra la solicitud,
el código HTTP y la respuesta). No borra volúmenes.

```bash
cp .env.example .env
docker compose up -d --build
bash docs/pruebas/pruebas-integrales.sh            # todo
bash docs/pruebas/pruebas-integrales.sh circuito   # o: crud | errores | timeout | caida | persistencia
```

Además, el CI ejecuta `pytest` de gateway y monitoreo y una prueba de humo con el stack completo
(incluido el Timeout).

## Colección de Postman

| Archivo | Contenido |
|---|---|
| [AgroSense-Gateway.postman_collection.json](postman/AgroSense-Gateway.postman_collection.json) | 43 solicitudes en 8 carpetas: Gateway, CRUD de Sensores, Mediciones y Umbrales, análisis y alertas, Circuit Breaker, Timeout y errores. Cada solicitud verifica su código HTTP y que la respuesta sea JSON. |
| [AgroSense-local.postman_environment.json](postman/AgroSense-local.postman_environment.json) | Entorno con `gateway = http://localhost:8000` |

Uso: en Postman, *Import* → los dos archivos → elegir el entorno «AgroSense local» → *Run collection*. Las
carpetas de CRUD guardan el id creado (`sensor_id`, `medicion_id`, `umbral_id`) y lo usan en los pasos
siguientes, así que se ejecutan en orden. La variable `{{gateway}}` también está en la colección, por lo que
funciona sin el entorno. Esta versión del Gateway no exige autenticación (*No Auth*); si se activa Basic Auth,
basta con cambiar la pestaña *Authorization* de la colección a `{{admin_user}}` / `{{admin_password}}`.

Desde la terminal (opcional): `npx newman run docs/pruebas/postman/AgroSense-Gateway.postman_collection.json`.
La carpeta «6. Timeout» deja la demora de Mediciones en 0 al terminar.

## Capturas de evidencia

Tomadas con el stack arriba (`docker compose up -d --build`); guardadas en [capturas/](capturas/).

| # | Captura | Comando / acción | Qué debe verse |
|---|---|---|---|
| 1 | [01-compose-ps.png](capturas/01-compose-ps.png) | `docker compose ps` | Contenedores `Up`, los de API y MySQL `healthy`; los microservicios sin puerto público y el Gateway en `8000`. En esta captura falta `home` porque el puerto `8080` estaba ocupado por otro programa del equipo donde se tomó |
| 2 | [02-postman-crud.png](capturas/02-postman-crud.png) | Solicitudes una por una contra el Gateway: `POST`, `GET`, `PUT`, `DELETE` y `GET` de `/sensores/<id>` | CRUD completo de Sensores: `201`, `200`, `200` (modificado), `200` y `404` final |
| 3 | [03-timeout-504.png](capturas/03-timeout-504.png) | `bash docs/pruebas/pruebas-integrales.sh timeout` (o carpeta «6. Timeout») | `504` «no respondió a tiempo» y luego `200` |
| 4 | [04-circuito-closed.png](capturas/04-circuito-closed.png) | `curl localhost:8000/monitoreo/circuitos` con todo arriba | `"estado":"CLOSED"`, contador 0 |
| 5 | [05-circuito-open.png](capturas/05-circuito-open.png) | `docker compose stop mediciones` + 3 × `curl localhost:8000/monitoreo/resumen-general` | `"estado":"OPEN"`, `503` «circuito abierto» |
| 6 | [06-circuito-half-open.png](capturas/06-circuito-half-open.png) | `docker compose start mediciones`, esperar 10 s, `curl …/monitoreo/circuitos` | `"estado":"HALF_OPEN"`; tras una solicitud correcta vuelve a `CLOSED` |
| 7 | [07-caida-sensores.png](capturas/07-caida-sensores.png) | `docker compose stop sensores` + `curl localhost:8000/sensores` | `503` en Sensores; Mediciones sigue en `200` |
| 8 | [08-recuperacion-sensores.png](capturas/08-recuperacion-sensores.png) | `docker compose start sensores` + `curl localhost:8000/sensores` | `200` de nuevo, sin reiniciar nada más |

La captura 2 une estas cinco solicitudes, que también están por separado en [capturas/crud/](capturas/crud/):
[1. POST](capturas/crud/02-1-post-crear.png) · [2. GET](capturas/crud/02-2-get-consultar.png) · [3. PUT](capturas/crud/02-3-put-modificar.png) · [4. DELETE](capturas/crud/02-4-delete-eliminar.png) · [5. GET 404](capturas/crud/02-5-get-404.png).

Los pasos 4–6 se pueden tomar todos de una vez con `bash docs/pruebas/pruebas-integrales.sh circuito`, que
imprime el estado del circuito en cada fase.

## Matriz de verificación

| Prueba | Resultado esperado | Resultado obtenido | Evidencia |
|---|---|---|---|
| Arquitectura completa | Todos los servicios requeridos están implementados | Sensores, Mediciones, Monitoreo, Gateway, Home y Simulador en ejecución (Notificaciones: fuera de alcance, documentado) | `docker compose ps` al inicio de [evidencia-ejecucion.txt](evidencia-ejecucion.txt) |
| Docker Compose | Componentes ejecutándose | 9 contenedores `Up`; los que tienen API, `healthy`; solo se publican 8080 y 8000 | idem |
| CRUD Sensores | Operaciones funcionales | POST 201, GET 200, PUT 200, modificación verificada, DELETE 200, GET posterior 404, id inexistente 404 | sección «CRUD Sensores» |
| CRUD Mediciones | Operaciones funcionales | Igual que arriba | sección «CRUD Mediciones» |
| CRUD Umbrales (Monitoreo) | Operaciones funcionales | Igual que arriba; `409` si ya existe un umbral para el tipo | sección «CRUD Umbrales» |
| Alertas (Monitoreo) | Lectura y borrado; se generan al evaluar | GET 200, GET inexistente 404, DELETE inexistente 404 | sección «Alertas» |
| Bases de datos | Persistencia independiente | Un MySQL y un volumen por servicio; los datos sobreviven a recrear los contenedores de aplicación | sección «Persistencia» |
| Comunicación HTTP | Intercambio correcto de información | Monitoreo obtiene lecturas de Mediciones y el tipo de Sensores (`resumen-general`, `evaluar`, `/monitoreo/<id>` → 200) | sección «Comunicación entre servicios» |
| Timeout | Error controlado por tiempo de espera | Con Mediciones demorando 6 s (> 3 s) Monitoreo responde `504` «no respondió a tiempo»; al poner la demora en 0 vuelve a `200` | sección «Timeout» |
| Circuit Breaker CLOSED | Comunicación permitida | Estado inicial `CLOSED`, contador 0; las fallas suben el contador 1 → 2 | sección «Circuit Breaker», pasos 1–2 |
| Circuit Breaker OPEN | Solicitudes protegidas rechazadas | A la 3.ª falla pasa a `OPEN`; la siguiente solicitud recibe `503` «circuito abierto» sin llamar a Mediciones, incluso con Mediciones ya recuperada | pasos 3–4 |
| HALF_OPEN y recuperación | Comunicación restablecida | Pasados 10 s el estado es `HALF_OPEN`; la solicitud de prueba responde `200` y el circuito vuelve a `CLOSED` con contador 0 | pasos 5–6 |
| Caída de un servicio | Fallan solo las operaciones dependientes | Con Sensores detenido: `GET /sensores` → 503; Mediciones sigue en 200; `evaluar` sigue en 200 (el tipo se deduce de la unidad); al reiniciarlo todo vuelve a 200 | sección «Simulación de fallos» |
| Gateway | Acceso a los servicios correspondientes | Todas las pruebas anteriores pasan por `:8000`; ruta desconocida → 404 | todo el archivo |
| Home | Acceso a una funcionalidad real | Home (`:8080`) consulta `/sensores`, `/mediciones` y `/monitoreo/*` a través del Gateway | manual |

## Respuestas HTTP verificadas

| Situación | Código | Dónde se observa |
|---|---|---|
| Solicitud correcta | 200 | consultas y actualizaciones |
| Recurso creado | 201 | POST de sensores, mediciones y umbrales |
| Datos inválidos | 400 | `POST /sensores` con `tipo` inválido |
| Recurso inexistente | 404 | id inexistente en cualquier servicio, ruta desconocida |
| Error interno | 500 | cualquier excepción no prevista responde JSON (`error interno del servidor`) |
| Dependencia con error | 502 | Mediciones devuelve un 5xx a Monitoreo |
| Dependencia no disponible | 503 | servicio detenido o circuito abierto |
| Tiempo de espera agotado | 504 | Mediciones lento (Monitoreo) o servicio que no responde al Gateway |

## Procedimiento manual (para la sustentación)

1. `docker compose up -d --build` y `docker compose ps`.
2. CRUD: `bash docs/pruebas/pruebas-integrales.sh crud` (o Postman con la colección de [postman/](postman/)).
3. Timeout: `bash docs/pruebas/pruebas-integrales.sh timeout`.
4. Circuit Breaker: `bash docs/pruebas/pruebas-integrales.sh circuito`; en paralelo,
   `watch -n1 "curl -s localhost:8000/monitoreo/circuitos"`.
5. Caída: `docker compose stop sensores` → probar → `docker compose start sensores`.
6. Persistencia: `bash docs/pruebas/pruebas-integrales.sh persistencia`.
