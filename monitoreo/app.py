import os
from contextlib import contextmanager

import mysql.connector
import requests
from flask import Flask, jsonify, request

from database import conectar, inicializar

app = Flask(__name__)

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')
SENSORES_URL = os.environ.get('SENSORES_URL', 'http://localhost:5003')

# Si el servicio Sensores no responde, el tipo se deduce de la unidad de la lectura.
TIPO_POR_UNIDAD = {'C': 'temperatura', '%': 'humedad'}


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
def error_base_datos(_err):
    return jsonify({'error': 'no se pudo conectar con la base de datos'}), 503


class MedicionesNoDisponible(Exception):
    pass


def consultar_mediciones(**params):
    """Consulta GET /mediciones del servicio Mediciones; lanza MedicionesNoDisponible si falla."""
    try:
        respuesta = requests.get(f'{MEDICIONES_URL}/mediciones', params=params, timeout=3)
    except requests.exceptions.Timeout:
        raise MedicionesNoDisponible('el servicio de Mediciones no respondió a tiempo')
    except requests.exceptions.RequestException:
        raise MedicionesNoDisponible('no se pudo conectar con el servicio de Mediciones')
    if respuesta.status_code != 200:
        raise MedicionesNoDisponible('el servicio de Mediciones devolvió un error')
    return respuesta.json()


@app.errorhandler(MedicionesNoDisponible)
def error_mediciones(err):
    return jsonify({'error': str(err)}), 503


def tipo_de_sensor(sensor_id, lectura):
    """Tipo del sensor según el servicio Sensores; respaldo: unidad de la lectura."""
    try:
        respuesta = requests.get(f'{SENSORES_URL}/sensores/{sensor_id}', timeout=2)
        if respuesta.status_code == 200:
            return respuesta.json().get('tipo')
    except (requests.exceptions.RequestException, ValueError):
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
    if not limite.isdigit() or int(limite) < 1:
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
    return jsonify(filas), 200


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
    """Métricas globales de todos los sensores."""
    lecturas = consultar_mediciones()
    if not lecturas:
        return jsonify({'mensaje': 'No hay lecturas registradas en la red'}), 200

    sensores = sorted({str(l['sensor_id']) for l in lecturas})
    valores = [float(l['valor']) for l in lecturas]
    return jsonify({
        'total_lecturas_sistema': len(lecturas),
        'total_sensores_activos': len(sensores),
        'listado_sensores': sensores,
        'promedio_global_sistema': round(sum(valores) / len(valores), 2),
    }), 200


@app.route('/monitoreo/evaluar/<sensor_id>', methods=['GET'])
def evaluar_sensor(sensor_id):
    """Compara la última lectura del sensor con el umbral de su tipo y registra la alerta."""
    lecturas = consultar_mediciones(sensor_id=sensor_id, limit=1)
    if not lecturas:
        return jsonify({'mensaje': f'Sin datos para evaluar el sensor {sensor_id}'}), 404

    ultima = lecturas[-1]
    valor = float(ultima['valor'])
    unidad = ultima.get('unidad') or ''
    tipo = tipo_de_sensor(sensor_id, ultima)

    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM umbrales WHERE tipo = %s', (tipo,))
        umbral = cursor.fetchone()

    if umbral is None:
        estado = 'SIN_UMBRAL'
        detalle = f'No hay umbral configurado para el tipo "{tipo}".'
    elif valor > umbral['maximo']:
        estado = 'ALERTA_CRITICA'
        detalle = f"El valor {valor} {unidad} supera el límite máximo permitido ({umbral['maximo']})."
    elif valor < umbral['minimo']:
        estado = 'ALERTA_CRITICA'
        detalle = f"El valor {valor} {unidad} está por debajo del límite mínimo permitido ({umbral['minimo']})."
    else:
        estado = 'NORMAL'
        detalle = 'El valor se encuentra dentro del rango operativo seguro.'

    if estado == 'ALERTA_CRITICA' and ultima.get('id') is not None:
        with cursor_bd(commit=True) as cursor:
            cursor.execute(
                'INSERT IGNORE INTO alertas (medicion_id, sensor_id, tipo, valor, estado, detalle, timestamp) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (ultima['id'], str(sensor_id), tipo, valor, estado, detalle, ultima.get('timestamp')),
            )

    return jsonify({
        'sensor_id': str(sensor_id),
        'tipo': tipo,
        'evaluacion': estado,
        'diagnostico': detalle,
        'valor_evaluado': valor,
        'timestamp_evaluado': ultima.get('timestamp'),
    }), 200


@app.route('/monitoreo/<sensor_id>', methods=['GET'])
def resumen_sensor(sensor_id):
    lecturas = consultar_mediciones(sensor_id=sensor_id)
    if not lecturas:
        return jsonify({'mensaje': f'El sensor {sensor_id} no tiene lecturas todavía'}), 404

    valores = [float(l['valor']) for l in lecturas]
    return jsonify({
        'sensor_id': str(sensor_id),
        'cantidad_lecturas': len(lecturas),
        'promedio': round(sum(valores) / len(valores), 2),
        'ultima_lectura': lecturas[-1],
    }), 200


if __name__ == '__main__':
    inicializar()
    app.run(host='0.0.0.0', port=5002)
