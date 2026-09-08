import os
import time
import random
import requests

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')
INTERVALO_SEGUNDOS = int(os.environ.get('INTERVALO_SEGUNDOS', 5))

TIPOS_SENSOR = {
    "temperatura": {"rango": (15, 40), "unidad": "C"},
    "humedad": {"rango": (20, 100), "unidad": "%"},
}

# Catálogo de sensores fijo (en este avance no existe un servicio de Sensores).
SENSORES = [
    {"id": 1, "tipo": "temperatura", "ubicacion": "sala"},
    {"id": 2, "tipo": "temperatura", "ubicacion": "cocina"},
    {"id": 3, "tipo": "humedad", "ubicacion": "invernadero"},
]


def esperar_servicio(url, nombre, intentos=20, espera=2):
    """Reintenta el health check de un servicio hasta que responda o se agoten los intentos."""
    for intento in range(1, intentos + 1):
        try:
            resp = requests.get(f"{url}/health", timeout=2)
            if resp.status_code == 200:
                print(f"[simulador] {nombre} disponible")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"[simulador] esperando a {nombre}... ({intento}/{intentos})")
        time.sleep(espera)
    return False


def generar_valor(tipo_sensor):
    config = TIPOS_SENSOR.get(tipo_sensor, TIPOS_SENSOR["temperatura"])
    minimo, maximo = config["rango"]
    valor = round(random.uniform(minimo, maximo), 2)
    return valor, config["unidad"]


def enviar_medicion(sensor):
    valor, unidad = generar_valor(sensor["tipo"])
    payload = {"sensor_id": sensor["id"], "valor": valor, "unidad": unidad}

    try:
        resp = requests.post(f"{MEDICIONES_URL}/mediciones", json=payload, timeout=5)
        if resp.status_code == 201:
            print(f"[simulador] enviado: sensor {sensor['id']} ({sensor['tipo']}) -> {valor}{unidad}")
        else:
            print(f"[simulador] error al enviar medición (HTTP {resp.status_code}): {resp.text}")
    except requests.exceptions.RequestException as err:
        print(f"[simulador] no se pudo conectar con mediciones: {err}")


def main():
    print("[simulador] iniciando...")

    if not esperar_servicio(MEDICIONES_URL, "mediciones"):
        print("[simulador] no se pudo conectar con mediciones, abortando")
        return

    print(f"[simulador] generando datos para {len(SENSORES)} sensor(es) cada {INTERVALO_SEGUNDOS}s")

    while True:
        for sensor in SENSORES:
            enviar_medicion(sensor)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()