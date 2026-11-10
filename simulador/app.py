import logging
import os
import random
import sys
import time

import requests

logger = logging.getLogger('simulador')

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')
INTERVALO_SEGUNDOS = int(os.environ.get('INTERVALO_SEGUNDOS', 5))
SENSORES_URL = os.environ.get('SENSORES_URL', 'http://localhost:5003')

TIPOS_SENSOR = {
    "temperatura": {"rango": (15, 40), "unidad": "C"},
    "humedad": {"rango": (20, 100), "unidad": "%"},
}

# Catálogo de respaldo: se usa solo si el servicio Sensores no responde.
SENSORES_RESPALDO = [
    {"id": 1, "tipo": "temperatura", "ubicacion": "sala"},
    {"id": 2, "tipo": "temperatura", "ubicacion": "cocina"},
    {"id": 3, "tipo": "humedad", "ubicacion": "invernadero"},
]

# Una sola sesión: reutiliza las conexiones HTTP en lugar de abrir una por cada lectura.
sesion = requests.Session()


def esperar_servicio(url, nombre, intentos=20, espera=2):
    """Reintenta el health check de un servicio hasta que responda o se agoten los intentos."""
    for intento in range(1, intentos + 1):
        try:
            resp = sesion.get(f"{url}/health", timeout=2)
            if resp.status_code == 200:
                logger.info("%s disponible", nombre)
                return True
        except requests.exceptions.RequestException:
            pass
        logger.info("esperando a %s… (%s/%s)", nombre, intento, intentos)
        time.sleep(espera)
    return False


def cargar_sensores():
    """Consulta el catálogo de sensores activos al servicio Sensores; usa el respaldo si falla."""
    try:
        resp = sesion.get(f"{SENSORES_URL}/sensores", params={"activo": "true"}, timeout=3)
        if resp.status_code == 200:
            sensores = resp.json()
            if sensores:
                return sensores
        logger.warning("sensores respondió HTTP %s, usando catálogo de respaldo", resp.status_code)
    except (requests.exceptions.RequestException, ValueError) as err:
        logger.warning("no se pudo consultar sensores (%s), usando catálogo de respaldo", err)
    return SENSORES_RESPALDO


def generar_valor(tipo_sensor):
    config = TIPOS_SENSOR.get(tipo_sensor, TIPOS_SENSOR["temperatura"])
    minimo, maximo = config["rango"]
    valor = round(random.uniform(minimo, maximo), 2)
    return valor, config["unidad"]


def enviar_medicion(sensor):
    valor, unidad = generar_valor(sensor["tipo"])
    payload = {"sensor_id": sensor["id"], "valor": valor, "unidad": unidad}

    try:
        resp = sesion.post(f"{MEDICIONES_URL}/mediciones", json=payload, timeout=5)
        if resp.status_code == 201:
            logger.info("enviado: sensor %s (%s) -> %s%s", sensor["id"], sensor["tipo"], valor, unidad)
        else:
            logger.error("error al enviar medición (HTTP %s): %s", resp.status_code, resp.text)
    except requests.exceptions.RequestException as err:
        logger.error("no se pudo conectar con mediciones: %s", err)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    logger.info("iniciando…")

    if not esperar_servicio(MEDICIONES_URL, "mediciones"):
        logger.error("no se pudo conectar con mediciones, abortando")
        sys.exit(1)  # código distinto de 0: Docker lo reinicia (restart: unless-stopped)

    logger.info("generando datos cada %ss", INTERVALO_SEGUNDOS)

    while True:
        for sensor in cargar_sensores():
            enviar_medicion(sensor)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
