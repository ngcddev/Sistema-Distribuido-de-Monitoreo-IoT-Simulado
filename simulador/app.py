import os
import time
import random
import requests

SENSORES_URL = os.environ.get('SENSORES_URL', 'http://localhost:5000')
MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')
INTERVALO_SEGUNDOS = int(os.environ.get('INTERVALO_SEGUNDOS', 5))

TIPOS_SENSOR = {
    "temperatura": {"rango": (15, 40), "unidad": "C"},
    "humedad": {"rango": (20, 100), "unidad": "%"},
}


SENSORES_POR_DEFECTO = [
    {"tipo": "temperatura", "ubicacion": "sala"},
    {"tipo": "temperatura", "ubicacion": "cocina"},
    {"tipo": "humedad", "ubicacion": "invernadero"},
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


def obtener_o_crear_sensores():
    """Obtiene el catálogo de sensores; si está vacío, crea unos por defecto."""
    resp = requests.get(f"{SENSORES_URL}/sensores", timeout=5)
    resp.raise_for_status()
    sensores = resp.json()

    if sensores:
        return sensores

    print("[simulador] no hay sensores registrados, creando sensores por defecto")
    creados = []
    for datos in SENSORES_POR_DEFECTO:
        resp = requests.post(f"{SENSORES_URL}/sensores", json=datos, timeout=5)
        resp.raise_for_status()
        creados.append(resp.json())
        print(f"[simulador] sensor creado: {creados[-1]}")

    return creados


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

    if not esperar_servicio(SENSORES_URL, "sensores"):
        print("[simulador] no se pudo conectar con sensores, abortando")
        return
    if not esperar_servicio(MEDICIONES_URL, "mediciones"):
        print("[simulador] no se pudo conectar con mediciones, abortando")
        return

    sensores = obtener_o_crear_sensores()
    print(f"[simulador] generando datos para {len(sensores)} sensor(es) cada {INTERVALO_SEGUNDOS}s")

    while True:
        for sensor in sensores:
            enviar_medicion(sensor)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()