import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import mysql.connector
import pybreaker
import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from database import conectar, inicializar

app = Flask(__name__)

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')
SENSORES_URL = os.environ.get('SENSORES_URL', 'http://localhost:5003')

# Timeout (segundos) de cada llamada HTTP a otro servicio; configurable por entorno.
MEDICIONES_TIMEOUT = float(os.environ.get('MEDICIONES_TIMEOUT', '3'))
SENSORES_TIMEOUT = float(os.environ.get('SENSORES_TIMEOUT', '2'))

# Circuit Breaker de cada dependencia: se abre tras CB_MAX_FAILS fallas técnicas seguidas
# (timeout, conexión rechazada o HTTP 5xx) y, pasados CB_TIMEOUT segundos, deja pasar una
# solicitud de prueba (HALF_OPEN). Un 404 o un 400 de la dependencia NO cuentan como falla.
CB_MAX_FAILS = int(os.environ.get('CB_MAX_FAILS', '3'))
CB_TIMEOUT = int(os.environ.get('CB_TIMEOUT', '10'))


class RegistroDeApertura(pybreaker.CircuitBreakerListener):
    """Anota cuándo se abrió el circuito: pybreaker solo pasa a HALF_OPEN al recibir la siguiente solicitud."""

    def __init__(self):
        self.abierto_desde = None

    def state_change(self, cb, old_state, new_state):
        self.abierto_desde = time.monotonic() if new_state.name == 'open' else None


def crear_circuito(nombre, fail_max=None, reset_timeout=None):
    circuito = pybreaker.CircuitBreaker(
        fail_max=CB_MAX_FAILS if fail_max is None else fail_max,
        reset_timeout=CB_TIMEOUT if reset_timeout is None else reset_timeout,
        name=nombre, throw_new_error_on_trip=True, listeners=[RegistroDeApertura()])
    return circuito


def estado_visible(circuito):
    """CLOSED, OPEN o HALF_OPEN. Un circuito abierto cuyo tiempo de recuperación ya venció se
    informa como HALF_OPEN: la próxima solicitud será la prueba que decide si se cierra o se reabre."""
    estado = circuito.current_state
    if estado == 'open':
        registro = circuito.listeners[0]
        if registro.abierto_desde is not None and time.monotonic() - registro.abierto_desde >= circuito.reset_timeout:
            return 'HALF_OPEN'
    return estado.upper().replace('-', '_')


circuito_mediciones = crear_circuito('mediciones')
circuito_sensores = crear_circuito('sensores')

# Si el servicio Sensores no responde, el tipo se deduce de la unidad de la lectura.
TIPO_POR_UNIDAD = {'C': 'temperatura', '%': 'humedad'}

# Códigos de MySQL/cliente que indican que no hay conexión (el resto son errores de la consulta).
ERRNOS_CONEXION = {1040, 2002, 2003, 2006, 2013, 2055}


@contextmanager
def cursor_bd(commit=False):
    """Abre una conexión, entrega un cursor y la cierra siempre."""
    conexion = conectar()
    try:
        cursor = conexion.cursor(dictionary=True)
        try:
            yield cursor
            if commit:
                conexion.commit()
        finally:
            cursor.close()
    finally:
        conexion.close()


@app.errorhandler(mysql.connector.IntegrityError)
def error_integridad(_err):
    return jsonify({'error': 'ya existe un umbral para ese tipo'}), 409


@app.errorhandler(mysql.connector.Error)
def error_base_datos(err):
    app.logger.error('Error de base de datos: %s', err, exc_info=err)
    if isinstance(err, mysql.connector.InterfaceError) or getattr(err, 'errno', None) in ERRNOS_CONEXION:
        return jsonify({'error': 'no se pudo conectar con la base de datos'}), 503
    return jsonify({'error': 'error interno de la base de datos'}), 500


@app.errorhandler(Exception)
def error_generico(err):
    """Cualquier error no previsto responde JSON (nunca la página HTML de Flask)."""
    if isinstance(err, HTTPException):
        return jsonify({'error': err.description}), err.code
    app.logger.exception(err)
    return jsonify({'error': 'error interno del servidor'}), 500


def a_iso(momento):
    """datetime sin zona (UTC, como lo guarda MySQL) -> texto ISO 8601 con +00:00."""
    return momento.replace(tzinfo=timezone.utc).isoformat()


def a_datetime_utc(texto):
    """Texto ISO 8601 -> datetime UTC sin zona para MySQL; None si falta o no es válido."""
    if not texto:
        return None
    try:
        momento = datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        return None
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    return momento


class MedicionesNoDisponible(Exception):
    """El servicio Mediciones no pudo atender la consulta. `codigo` es el HTTP a devolver."""

    def __init__(self, mensaje, codigo=503):
        super().__init__(mensaje)
        self.codigo = codigo


def consultar_mediciones(ruta='/mediciones', **params):
    """Consulta GET <ruta> del servicio Mediciones, protegida con timeout y Circuit Breaker.

    Errores: 504 si se agota el timeout, 503 si no hay conexión o el circuito está abierto,
    502 si Mediciones responde con un error que no es 5xx.
    """
    try:
        with circuito_mediciones.calling():
            respuesta = requests.get(f'{MEDICIONES_URL}{ruta}', params=params, timeout=MEDICIONES_TIMEOUT)
            if respuesta.status_code >= 500:
                respuesta.raise_for_status()  # cuenta como falla técnica del circuito
    except pybreaker.CircuitBreakerError:
        raise MedicionesNoDisponible('el servicio de Mediciones no está disponible (circuito abierto)', 503)
    except requests.exceptions.Timeout:
        raise MedicionesNoDisponible('el servicio de Mediciones no respondió a tiempo', 504)
    except requests.exceptions.HTTPError:
        raise MedicionesNoDisponible('el servicio de Mediciones devolvió un error interno', 502)
    except requests.exceptions.RequestException:
        raise MedicionesNoDisponible('no se pudo conectar con el servicio de Mediciones', 503)
    if respuesta.status_code != 200:
        raise MedicionesNoDisponible('el servicio de Mediciones devolvió un error', 502)
    return respuesta.json()


@app.errorhandler(MedicionesNoDisponible)
def error_mediciones(err):
    return jsonify({'error': str(err)}), err.codigo


def tipo_de_sensor(sensor_id, lectura):
    """Tipo del sensor según el servicio Sensores; respaldo: unidad de la lectura.

    La consulta está protegida con timeout y Circuit Breaker; si falla, no se interrumpe la
    evaluación: se deduce el tipo de la unidad de la lectura.
    """
    try:
        with circuito_sensores.calling():
            respuesta = requests.get(f'{SENSORES_URL}/sensores/{sensor_id}', timeout=SENSORES_TIMEOUT)
            if respuesta.status_code >= 500:
                respuesta.raise_for_status()
        if respuesta.status_code == 200:
            return respuesta.json().get('tipo')
    except (pybreaker.CircuitBreakerError, requests.exceptions.RequestException, ValueError):
        pass
    return TIPO_POR_UNIDAD.get(lectura.get('unidad'))


def numero(valor):
    if isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


@app.route('/health', methods=['GET'])
def health_check():
    try:
        with cursor_bd() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except mysql.connector.Error:
        return jsonify({'status': 'error', 'detalle': 'base de datos no disponible'}), 503
    return jsonify({'status': 'ok'}), 200


# ---------------------------------------------------------------- Umbrales (CRUD)

def validar_umbral(data):
    """Devuelve (umbral, error). Exige tipo, minimo y maximo."""
    if not isinstance(data, dict) or not all(k in data for k in ('tipo', 'minimo', 'maximo')):
        return None, 'tipo, minimo y maximo son requeridos'
    tipo = data['tipo']
    if not isinstance(tipo, str) or not tipo.strip() or len(tipo) > 30:
        return None, 'tipo debe ser texto de 1 a 30 caracteres'
    minimo, maximo = numero(data['minimo']), numero(data['maximo'])
    if minimo is None or maximo is None:
        return None, 'minimo y maximo deben ser numéricos'
    if minimo >= maximo:
        return None, 'minimo debe ser menor que maximo'
    unidad = data.get('unidad')
    if unidad is not None and (not isinstance(unidad, str) or len(unidad) > 10):
        return None, 'unidad debe ser texto de máximo 10 caracteres'
    return {'tipo': tipo.strip().lower(), 'minimo': minimo, 'maximo': maximo, 'unidad': unidad}, None


@app.route('/monitoreo/umbrales', methods=['GET'])
def listar_umbrales():
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM umbrales ORDER BY id')
        filas = cursor.fetchall()
    return jsonify(filas), 200


@app.route('/monitoreo/umbrales/<int:umbral_id>', methods=['GET'])
def obtener_umbral(umbral_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM umbrales WHERE id = %s', (umbral_id,))
        fila = cursor.fetchone()
    if not fila:
        return jsonify({'error': 'umbral no encontrado'}), 404
    return jsonify(fila), 200


@app.route('/monitoreo/umbrales', methods=['POST'])
def crear_umbral():
    umbral, error = validar_umbral(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'INSERT INTO umbrales (tipo, minimo, maximo, unidad) VALUES (%s, %s, %s, %s)',
            (umbral['tipo'], umbral['minimo'], umbral['maximo'], umbral['unidad']),
        )
        umbral['id'] = cursor.lastrowid
    return jsonify(umbral), 201


@app.route('/monitoreo/umbrales/<int:umbral_id>', methods=['PUT'])
def actualizar_umbral(umbral_id):
    umbral, error = validar_umbral(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'UPDATE umbrales SET tipo = %s, minimo = %s, maximo = %s, unidad = %s WHERE id = %s',
            (umbral['tipo'], umbral['minimo'], umbral['maximo'], umbral['unidad'], umbral_id),
        )
        if cursor.rowcount == 0:
            return jsonify({'error': 'umbral no encontrado'}), 404
    umbral['id'] = umbral_id
    return jsonify(umbral), 200


@app.route('/monitoreo/umbrales/<int:umbral_id>', methods=['DELETE'])
def eliminar_umbral(umbral_id):
    with cursor_bd(commit=True) as cursor:
        cursor.execute('DELETE FROM umbrales WHERE id = %s', (umbral_id,))
        eliminado = cursor.rowcount > 0
    if not eliminado:
        return jsonify({'error': 'umbral no encontrado'}), 404
    return jsonify({'mensaje': 'umbral eliminado correctamente', 'id': umbral_id}), 200


# ---------------------------------------------------------------- Alertas

@app.route('/monitoreo/alertas', methods=['GET'])
def listar_alertas():
    """Alertas generadas al evaluar sensores. Filtros: ?sensor_id= , ?limit= (por defecto 50)."""
    limite = request.args.get('limit', '50')
    if not limite.isascii() or not limite.isdigit() or int(limite) < 1:
        return jsonify({'error': 'limit debe ser un entero positivo'}), 400

    consulta, parametros = 'SELECT * FROM alertas', []
    sensor_id = request.args.get('sensor_id')
    if sensor_id:
        consulta += ' WHERE sensor_id = %s'
        parametros.append(sensor_id)
    consulta += ' ORDER BY id DESC LIMIT %s'
    parametros.append(min(int(limite), 500))

    with cursor_bd() as cursor:
        cursor.execute(consulta, parametros)
        filas = cursor.fetchall()
    for fila in filas:
        if isinstance(fila.get('timestamp'), datetime):
            fila['timestamp'] = a_iso(fila['timestamp'])
    return jsonify(filas), 200


@app.route('/monitoreo/alertas/<int:alerta_id>', methods=['GET'])
def obtener_alerta(alerta_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM alertas WHERE id = %s', (alerta_id,))
        fila = cursor.fetchone()
    if not fila:
        return jsonify({'error': 'alerta no encontrada'}), 404
    if isinstance(fila.get('timestamp'), datetime):
        fila['timestamp'] = a_iso(fila['timestamp'])
    return jsonify(fila), 200


@app.route('/monitoreo/alertas/<int:alerta_id>', methods=['DELETE'])
def eliminar_alerta(alerta_id):
    with cursor_bd(commit=True) as cursor:
        cursor.execute('DELETE FROM alertas WHERE id = %s', (alerta_id,))
        eliminada = cursor.rowcount > 0
    if not eliminada:
        return jsonify({'error': 'alerta no encontrada'}), 404
    return jsonify({'mensaje': 'alerta eliminada correctamente', 'id': alerta_id}), 200


# ---------------------------------------------------------------- Análisis de mediciones

@app.route('/monitoreo/resumen-general', methods=['GET'])
def resumen_general():
    """Métricas globales de todos los sensores (calculadas por Mediciones en SQL)."""
    estadisticas = consultar_mediciones('/mediciones/estadisticas')
    if not estadisticas['total']:
        return jsonify({'mensaje': 'No hay lecturas registradas en la red'}), 200

    sensores = [str(sensor) for sensor in estadisticas['sensores']]
    return jsonify({
        'total_lecturas_sistema': estadisticas['total'],
        'total_sensores_activos': len(sensores),
        'listado_sensores': sensores,
        # Un promedio por unidad: promediar °C con % no tiene sentido.
        'promedios_por_unidad': {
            (grupo['unidad'] or 'sin unidad'): grupo['promedio'] for grupo in estadisticas['por_unidad']
        },
    }), 200


def clasificar(valor, unidad, tipo, umbral):
    """Devuelve (estado, detalle) de una lectura frente al umbral de su tipo (umbral puede ser None)."""
    if umbral is None:
        return 'SIN_UMBRAL', f'No hay umbral configurado para el tipo "{tipo}".'
    if valor > umbral['maximo']:
        return 'ALERTA_CRITICA', f"El valor {valor} {unidad} supera el límite máximo permitido ({umbral['maximo']})."
    if valor < umbral['minimo']:
        return 'ALERTA_CRITICA', f"El valor {valor} {unidad} está por debajo del límite mínimo permitido ({umbral['minimo']})."
    return 'NORMAL', 'El valor se encuentra dentro del rango operativo seguro.'


def evaluar_lectura(sensor_id, lectura, registrar=True):
    """Compara una lectura con el umbral de su tipo y, si está fuera de rango, registra la alerta.

    Con registrar=False solo calcula la evaluación, sin escribir en la BD.
    Se guarda una sola alerta por medición (INSERT IGNORE sobre medicion_id único).
    """
    valor = float(lectura['valor'])
    unidad = lectura.get('unidad') or ''
    tipo = tipo_de_sensor(sensor_id, lectura)

    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM umbrales WHERE tipo = %s', (tipo,))
        umbral = cursor.fetchone()

    estado, detalle = clasificar(valor, unidad, tipo, umbral)

    registrada = False
    if registrar and estado == 'ALERTA_CRITICA' and lectura.get('id') is not None:
        with cursor_bd(commit=True) as cursor:
            cursor.execute(
                'INSERT IGNORE INTO alertas (medicion_id, sensor_id, tipo, valor, estado, detalle, timestamp) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (lectura['id'], str(sensor_id), tipo, valor, estado, detalle,
                 a_datetime_utc(lectura.get('timestamp'))),
            )
            registrada = True

    return {
        'sensor_id': str(sensor_id),
        'tipo': tipo,
        'evaluacion': estado,
        'diagnostico': detalle,
        'valor_evaluado': valor,
        'timestamp_evaluado': lectura.get('timestamp'),
        'alerta_registrada': registrada,
    }


@app.route('/monitoreo/evaluar/<sensor_id>', methods=['GET', 'POST'])
def evaluar_sensor(sensor_id):
    """Evalúa la última lectura del sensor.

    GET solo consulta (compatible con clientes anteriores): no escribe en la BD.
    POST además registra la alerta si la lectura está fuera de rango.
    Las lecturas nuevas también las evalúa de forma automática el worker (worker.py).
    """
    lecturas = consultar_mediciones(sensor_id=sensor_id, limit=1)
    if not lecturas:
        return jsonify({'mensaje': f'Sin datos para evaluar el sensor {sensor_id}'}), 404
    resultado = evaluar_lectura(sensor_id, lecturas[-1], registrar=request.method == 'POST')
    return jsonify(resultado), 200


@app.route('/monitoreo/circuitos', methods=['GET'])
def estado_circuitos():
    """Estado de los Circuit Breakers (CLOSED / OPEN / HALF_OPEN) y su configuración."""
    def describir(circuito, timeout):
        return {
            'estado': estado_visible(circuito),
            'contador_fallos': circuito.fail_counter,
            'umbral_fallos': circuito.fail_max,
            'tiempo_recuperacion_segundos': circuito.reset_timeout,
            'timeout_solicitud_segundos': timeout,
        }
    return jsonify({
        'mediciones': describir(circuito_mediciones, MEDICIONES_TIMEOUT),
        'sensores': describir(circuito_sensores, SENSORES_TIMEOUT),
    }), 200


@app.route('/monitoreo/<sensor_id>', methods=['GET'])
def resumen_sensor(sensor_id):
    estadisticas = consultar_mediciones('/mediciones/estadisticas', sensor_id=sensor_id)
    lecturas = consultar_mediciones(sensor_id=sensor_id, limit=1) if estadisticas['total'] else []
    if not lecturas:
        return jsonify({'mensaje': f'El sensor {sensor_id} no tiene lecturas todavía'}), 404

    return jsonify({
        'sensor_id': str(sensor_id),
        'cantidad_lecturas': estadisticas['total'],
        'promedio': estadisticas['promedio'],
        'ultima_lectura': lecturas[-1],
    }), 200


if __name__ == '__main__':
    # Solo para desarrollo local; en el contenedor se ejecuta con gunicorn (ver gunicorn_conf.py).
    if not inicializar():
        sys.exit('[monitoreo] no se pudo preparar la base de datos')
    app.run(host='0.0.0.0', port=5002)
