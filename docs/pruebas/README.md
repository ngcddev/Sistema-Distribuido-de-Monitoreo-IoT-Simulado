# Pruebas del tercer avance

Todas las pruebas se ejecutan **sobre el stack real** (`docker compose up -d --build`) y **a través del API
Gateway** (`http://localhost:8000`). El script [pruebas-integrales.sh](pruebas-integrales.sh) las automatiza y
su salida completa está en [evidencia-ejecucion.txt](evidencia-ejecucion.txt) (cada línea muestra la solicitud,
el código HTTP y la respuesta). No borra volúmenes.

```bash
cp .env.example .env            # y cambiar las contraseñas
docker compose up -d --build
bash docs/pruebas/pruebas-integrales.sh            # todo
bash docs/pruebas/pruebas-integrales.sh circuito   # o: crud | errores | timeout | caida | persistencia
```

Además, el CI ejecuta `pytest` por servicio (gateway, mediciones, monitoreo, sensores y simulador), las pruebas
de navegador del Home y una prueba de humo con el stack completo.

## Matriz de verificación

| Prueba | Resultado esperado | Resultado obtenido | Evidencia |
|---|---|---|---|
| Arquitectura completa | Todos los servicios requeridos están implementados | Sensores, Mediciones, Monitoreo, Gateway, Home, Evaluador, Purgador y Simulador en ejecución (Notificaciones: fuera de alcance, documentado) | `docker compose ps` al inicio de [evidencia-ejecucion.txt](evidencia-ejecucion.txt) |
| Docker Compose | Componentes ejecutándose | 11 contenedores `Up`; los que tienen API, `healthy`; solo se publican 8080 y 8000 | idem |
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
| Gateway | Acceso a los servicios correspondientes | Todas las pruebas anteriores pasan por `:8000`; sin credenciales, escribir → 401; ruta desconocida → 404 | todo el archivo |
| Home | Acceso a una funcionalidad real | Home (`:8080`) consulta `/sensores`, `/mediciones` y `/monitoreo/*` a través del Gateway; escribir sin credenciales → 401 y con credenciales → 201 | manual + `home/e2e` en CI |

## Respuestas HTTP verificadas

| Situación | Código | Dónde se observa |
|---|---|---|
| Solicitud correcta | 200 | consultas y actualizaciones |
| Recurso creado | 201 | POST de sensores, mediciones y umbrales |
| Datos inválidos | 400 | `POST /sensores` con `tipo` inválido |
| Sin credenciales | 401 | escribir sin `Authorization` |
| Recurso inexistente | 404 | id inexistente en cualquier servicio, ruta desconocida |
| Error interno | 500 | cualquier excepción no prevista responde JSON (`error interno del servidor`) |
| Dependencia con error | 502 | Mediciones devuelve un 5xx a Monitoreo |
| Dependencia no disponible | 503 | servicio detenido o circuito abierto |
| Tiempo de espera agotado | 504 | Mediciones lento (Monitoreo) o servicio que no responde al Gateway |

## Procedimiento manual (para la sustentación)

1. `docker compose up -d --build` y `docker compose ps`.
2. CRUD: `bash docs/pruebas/pruebas-integrales.sh crud` (o Postman con [docs/endpoints](../endpoints/)).
3. Timeout: `bash docs/pruebas/pruebas-integrales.sh timeout`.
4. Circuit Breaker: `bash docs/pruebas/pruebas-integrales.sh circuito`; en paralelo,
   `watch -n1 "curl -s localhost:8000/monitoreo/circuitos"`.
5. Caída: `docker compose stop sensores` → probar → `docker compose start sensores`.
6. Persistencia: `bash docs/pruebas/pruebas-integrales.sh persistencia`.
