"""API Gateway: punto de entrada único hacia Sensores, Mediciones y Monitoreo.

No implementa lógica de negocio ni toca bases de datos: identifica el servicio por el primer
segmento de la ruta, reenvía método, query, cuerpo y respuesta (con su código HTTP) y traduce
los fallos de comunicación a errores HTTP claros (503 servicio caído, 504 tiempo agotado).
"""
import logging
import os

import requests
from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Direcciones internas (nombres de servicio dentro de la red de Docker Compose).
SERVICIOS = {
    'sensores': os.environ.get('SENSOR_SERVICE_URL', 'http://sensores:5003'),
    'mediciones': os.environ.get('MEDICIONES_SERVICE_URL', 'http://mediciones:5001'),
    'monitoreo': os.environ.get('MONITOREO_SERVICE_URL', 'http://monitoreo:5002'),
}

# Timeout (segundos) de cada solicitud reenviada. Debe ser mayor que los timeouts internos de
# Monitoreo (para que sea Monitoreo quien responda su propio 504 y no el Gateway).
GATEWAY_TIMEOUT = float(os.environ.get('GATEWAY_TIMEOUT', '8'))

CABECERAS_RESPUESTA = ('Content-Type', 'Retry-After')


@app.errorhandler(Exception)
def error_generico(err):
    """Cualquier error responde JSON, nunca la página HTML de Flask."""
    if isinstance(err, HTTPException):
        return jsonify({'error': err.description}), err.code
    app.logger.exception(err)
    return jsonify({'error': 'error interno del servidor'}), 500


@app.route('/health', methods=['GET'])
def salud():
    """Estado del Gateway y de cada servicio al que enruta."""
    estado = {}
    for nombre, url in SERVICIOS.items():
        try:
            respuesta = requests.get(f'{url}/health', timeout=3)
            estado[nombre] = 'ok' if respuesta.status_code == 200 else f'error {respuesta.status_code}'
        except requests.exceptions.RequestException:
            estado[nombre] = 'no disponible'
    return jsonify({'gateway': 'ok', 'servicios': estado}), 200


@app.route('/', methods=['GET'])
def raiz():
    return jsonify({'gateway': 'AgroSense', 'rutas': {f'/{n}': url for n, url in SERVICIOS.items()}}), 200


@app.route('/<servicio>', defaults={'resto': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@app.route('/<servicio>/<path:resto>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def reenviar(servicio, resto):
    base = SERVICIOS.get(servicio)
    if base is None:
        return jsonify({'error': f'ruta desconocida: /{servicio}'}), 404

    destino = f'{base}/{servicio}' + (f'/{resto}' if resto else '')
    cabeceras = {}
    if request.content_type:
        cabeceras['Content-Type'] = request.content_type
    try:
        respuesta = requests.request(
            request.method, destino, params=request.args, data=request.get_data(),
            headers=cabeceras, timeout=GATEWAY_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return jsonify({'error': f'el servicio de {servicio} no respondió a tiempo'}), 504
    except requests.exceptions.RequestException:
        return jsonify({'error': f'el servicio de {servicio} no está disponible'}), 503

    # Se conservan el cuerpo y el código de estado tal cual los devolvió el servicio.
    salida = Response(respuesta.content, status=respuesta.status_code)
    for nombre in CABECERAS_RESPUESTA:
        if nombre in respuesta.headers:
            salida.headers[nombre] = respuesta.headers[nombre]
    return salida


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
