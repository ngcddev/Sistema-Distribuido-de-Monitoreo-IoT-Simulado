# Servicio 3: Simulador

## Resumen

Proceso que genera valores aleatorios de temperatura y humedad, consulta el catálogo de sensores y envía mediciones periódicamente.

## Responsabilidades

- Esperar la disponibilidad de Sensores y Mediciones.
- Consultar sensores existentes.
- Crear sensores predeterminados si el catálogo está vacío.
- Generar valores dentro de rangos definidos.
- Enviar mediciones en intervalos configurables.

## Información técnica

| Elemento | Valor |
|---|---|
| Código | `simulador/app.py` |
| Tipo | Proceso de fondo |
| API propia | No expone endpoints HTTP |
| Intervalo predeterminado | `5` segundos |

## Ejecución local

```bash
python simulador/app.py
```

El proceso continúa ejecutándose hasta que se detiene manualmente.

## Configuración

| Variable | Valor predeterminado | Descripción |
|---|---|---|
| `SENSORES_URL` | `http://localhost:5000` | URL base del servicio de Sensores |
| `MEDICIONES_URL` | `http://localhost:5001` | URL base del servicio de Mediciones |
| `INTERVALO_SEGUNDOS` | `5` | Tiempo entre ciclos de envío |

## Flujo de operación

1. Comprueba `GET /health` en Sensores.
2. Comprueba `GET /health` en Mediciones.
3. Consulta `GET /sensores`.
4. Si el catálogo está vacío, crea sensores mediante `POST /sensores`.
5. Genera un valor aleatorio según el tipo de sensor.
6. Registra la medición mediante `POST /mediciones`.
7. Espera el intervalo configurado y repite el ciclo.

## Tipos simulados

| Tipo | Rango | Unidad |
|---|---:|---|
| `temperatura` | 15 a 40 | `C` |
| `humedad` | 20 a 100 | `%` |

Si se recibe un tipo no definido, se utiliza la configuración de temperatura.

## Sensores predeterminados

Cuando el catálogo está vacío, el proceso intenta crear:

- Temperatura en `sala`.
- Temperatura en `cocina`.
- Humedad en `invernadero`.

## Integración

| Servicio | Operaciones consumidas |
|---|---|
| Sensores | `GET /health`, `GET /sensores`, `POST /sensores` |
| Mediciones | `GET /health`, `POST /mediciones` |

## Estado de integración

El código del Simulador existe, pero el `docker-compose.yml` actual solo levanta `mediciones` y `monitoreo`. Para ejecutar el flujo completo en contenedores, todavía falta integrar Sensores y Simulador en Compose.
