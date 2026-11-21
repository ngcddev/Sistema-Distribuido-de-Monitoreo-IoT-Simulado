"""API Gateway: punto de entrada único hacia Sensores, Mediciones y Monitoreo.

No implementa lógica de negocio ni toca bases de datos: identifica el servicio por el primer
segmento de la ruta, reenvía método, query, cuerpo y respuesta (con su código HTTP) y traduce
los fallos de comunicación a errores HTTP claros (503 servicio caído, 504 tiempo agotado).
"""
import hmac
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

# Si hay credenciales configuradas, modificar datos (POST/PUT/PATCH/DELETE) exige HTTP Basic.
ADMIN_USER = os.environ.get('GATEWAY_ADMIN_USER', '')
ADMIN_PASSWORD = os.environ.get('GATEWAY_ADMIN_PASSWORD', '')
METODOS_LECTURA = {'GET', 'HEAD', 'OPTIONS'}
# Evaluar un sensor es idempotente y solo deriva datos existentes: no pide credenciales.
RUTA_LIBRE = ('monitoreo', 'evaluar')

CABECERAS_RESPUESTA = ('Content-Type', 'Retry-After')


@app.errorhandler(Exception)
def error_generico(err):
    """Cualquier error responde JSON, nunca la página HTML de Flask."""
    if isinstance(err, HTTPException):
        return jsonify({'error': err.description}), err.code
    app.logger.exception(err)
    return jsonify({'error': 'error interno del servidor'}), 500


def requiere_credenciales(servicio, resto):
    if not ADMIN_USER or request.method in METODOS_LECTURA:
        return False
    return not (servicio == RUTA_LIBRE[0] and resto.split('/')[0] == RUTA_LIBRE[1])


def credenciales_validas():
    autorizacion = request.authorization
    if not autorizacion or autorizacion.username is None or autorizacion.password is None:
        return False
    usuario_ok = hmac.compare_digest(autorizacion.username.encode(), ADMIN_USER.encode())
    clave_ok = hmac.compare_digest(autorizacion.password.encode(), ADMIN_PASSWORD.encode())
    return usuario_ok and clave_ok


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

    if requiere_credenciales(servicio, resto) and not credenciales_validas():
        respuesta = jsonify({'error': 'se requieren credenciales de administrador para modificar datos'})
        respuesta.status_code = 401
        respuesta.headers['WWW-Authenticate'] = 'Basic realm="AgroSense admin"'
        return respuesta

    destino = f'{base}/{servicio}' + (f'/{resto}' if resto else '')
    cabeceras = {}
    if request.content_type:
        cabeceras['Content-Type'] = request.content_type  # las credenciales NO se reenvían
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
