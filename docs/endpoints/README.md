# Endpoints

Todas las rutas se pueden usar **a través del API Gateway** (`http://localhost:8000`), que es el punto de
entrada recomendado. Las mismas rutas existen directamente en cada servicio (puertos internos `5001`, `5002` y
`5003`, publicados solo con `compose.dev.yaml`).

Escribir (`POST`, `PUT`, `PATCH`, `DELETE`) exige HTTP Basic con `HOME_ADMIN_USER` / `HOME_ADMIN_PASSWORD`
(excepto `POST /monitoreo/evaluar/<id>`). En Postman: pestaña *Authorization → Basic Auth*.

- [ejemplos-gateway.md](ejemplos-gateway.md): ejemplos de cada endpoint por el Gateway, con cuerpos JSON.
- [postman-endpoints.txt](postman-endpoints.txt): lista de URLs para copiar en Postman.
- Referencia completa de cada servicio (entradas, salidas y códigos de respuesta):
  [Sensores](../servicios/servicio-sensores.md), [Mediciones](../servicios/servicio-1-mediciones.md),
  [Monitoreo](../servicios/servicio-2-monitoreo.md), [Gateway](../servicios/servicio-gateway.md).

## Resumen de recursos (CRUD)

| Servicio | Recurso | GET lista | GET `/<id>` | POST | PUT | DELETE |
|---|---|---|---|---|---|---|
| Sensores | `/sensores` | sí | sí | sí | sí | sí |
| Mediciones | `/mediciones` | sí | sí | sí | sí (y PATCH) | sí |
| Monitoreo | `/monitoreo/umbrales` | sí | sí | sí | sí | sí |
| Monitoreo | `/monitoreo/alertas` | sí | sí | — | — | sí |

**Operaciones que no son CRUD (justificación):**

| Endpoint | Por qué no es CRUD |
|---|---|
| `GET/POST /monitoreo/evaluar/<sensor_id>` | Es un cálculo: compara la última lectura con el umbral de su tipo. Las alertas no se crean ni se editan a mano: las genera la evaluación (por eso no tienen POST ni PUT). |
| `GET /monitoreo/resumen-general`, `GET /monitoreo/<sensor_id>` | Consultas agregadas (promedios, totales) sobre datos de Mediciones. |
| `GET /mediciones/estadisticas`, `GET /mediciones/sensor/<id>` | Consultas derivadas de las lecturas. |
| `GET /monitoreo/circuitos` | Diagnóstico del Circuit Breaker. |
| `GET/PUT /mediciones/simulacion/demora` | Herramienta de pruebas para simular una respuesta lenta (Timeout). |
| `GET /health` | Estado del servicio y de su base de datos. |
