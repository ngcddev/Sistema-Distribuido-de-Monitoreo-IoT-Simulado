from flask import Flask, request, jsonify, Response
from werkzeug.exceptions import HTTPException
import requests
import os


app = Flask(__name__)


@app.errorhandler(Exception)
def error_generico(err):
    """Responde JSON ante cualquier error, sin páginas HTML de Flask."""
    if isinstance(err, HTTPException):
        return jsonify({"error": err.description}), err.code
    app.logger.exception(err)
    return jsonify({"error": "error interno del servidor"}), 500

# Agregamos las variables de entonrno para poder llamar y que este se encargeu de comportar como el puerto de  elnace para los otros servicios


# Configuración de servicios
SENSOR_SERVICE_URL = os.getenv("SENSOR_SERVICE_URL", "http://sensores:5003")
MONITOREO_SERVICE_URL = os.getenv("MONITOREO_SERVICE_URL", "http://monitoreo:5002")
MEDICIONES_SERVICE_URL = os.getenv("MEDICIONES_SERVICE_URL", "http://mediciones:5001")


def rutador_servicios(metodo, url):
    try:
        respuesta = requests.request(metodo, url, params=request.args, json=request.get_json(silent=True), timeout=5)
        return Response(respuesta.content, status= respuesta.status_code,
                        content_type=respuesta.headers.get('content-type', 'application/json'))
    except requests.exceptions.Timeout:
        return jsonify({
            "mensaje": "Timeout - El servicio no respondió a tiempo"
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "mensaje": "Error de conexión - El servicio no está disponible"
        }), 502


# health general del gateway

@app.route("/health", methods=["GET"])
def salud_general():
    servicios = {
        "sensores": SENSOR_SERVICE_URL,
        "mediciones": MEDICIONES_SERVICE_URL,
        "monitoreo": MONITOREO_SERVICE_URL,
    }
    estado = {}
    for nombre, url in servicios.items():
        try:
            resp = requests.get(f"{url}/health", timeout=3)
            estado[nombre] = "ok" if resp.status_code == 200 else f"error {resp.status_code}"
        except requests.exceptions.RequestException:
            estado[nombre] = "no disponible"
    return jsonify({"status": estado, "mensaje": "estado de los servicios"}), 200


# apis de sensores

@app.route("/sensores", methods=["GET", "POST"])
def manejar_sensores():
    return rutador_servicios(request.method, f"{SENSOR_SERVICE_URL}/sensores")


@app.route("/sensores/<int:sensor_id>", methods=["GET", "PUT", "DELETE"])
def manejar_sensor(sensor_id):
    return rutador_servicios(request.method, f"{SENSOR_SERVICE_URL}/sensores/{sensor_id}")


# apis de mediciones

@app.route("/mediciones", methods=["GET", "POST"])
def manejar_mediciones():
    return rutador_servicios(request.method, f"{MEDICIONES_SERVICE_URL}/mediciones")


@app.route("/mediciones/sensor/<sensor_id>", methods=["GET"])
def manejar_mediciones_por_sensor(sensor_id):
    return rutador_servicios(request.method, f"{MEDICIONES_SERVICE_URL}/mediciones/sensor/{sensor_id}")


@app.route("/mediciones/<int:medicion_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
def manejar_medicion(medicion_id):
    return rutador_servicios(request.method, f"{MEDICIONES_SERVICE_URL}/mediciones/{medicion_id}")


# apis de monitoreo

@app.route("/monitoreo/umbrales", methods=["GET", "POST"])
def manejar_umbrales():
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/umbrales")


@app.route("/monitoreo/umbrales/<int:umbral_id>", methods=["GET", "PUT", "DELETE"])
def manejar_umbral(umbral_id):
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/umbrales/{umbral_id}")


@app.route("/monitoreo/alertas", methods=["GET"])
def manejar_alertas():
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/alertas")


@app.route("/monitoreo/alertas/<int:alerta_id>", methods=["DELETE"])
def manejar_alerta(alerta_id):
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/alertas/{alerta_id}")


@app.route("/monitoreo/resumen-general", methods=["GET"])
def resumen_general():
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/resumen-general")


@app.route("/monitoreo/evaluar/<sensor_id>", methods=["GET"])
def evaluar_sensor(sensor_id):
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/evaluar/{sensor_id}")


@app.route("/monitoreo/circuitos", methods=["GET"])
def estado_circuitos():
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/circuitos")


@app.route("/monitoreo/<sensor_id>", methods=["GET"])
def resumen_sensor(sensor_id):
    return rutador_servicios(request.method, f"{MONITOREO_SERVICE_URL}/monitoreo/{sensor_id}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
