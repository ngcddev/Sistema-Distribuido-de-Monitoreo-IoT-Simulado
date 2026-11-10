import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

import mysql.connector
import requests
from flask import Flask, jsonify, request

from database import conectar, inicializar

app = Flask(__name__)

LIMITE_MAXIMO = 1000
LIMITE_POR_DEFECTO = 100

# Si está definida, Mediciones comprueba que el sensor exista en el servicio Sensores.
SENSORES_URL = os.environ.get('SENSORES_URL')

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


@app.errorhandler(mysql.connector.Error)
def error_base_datos(err):
    app.logger.error('Error de base de datos: %s', err, exc_info=err)
    if isinstance(err, mysql.connector.InterfaceError) or getattr(err, 'errno', None) in ERRNOS_CONEXION:
        return jsonify({'error': 'no se pudo conectar con la base de datos'}), 503
    return jsonify({'error': 'error interno de la base de datos'}), 500


def a_iso(momento):
    """datetime sin zona (UTC, como lo guarda MySQL) -> texto ISO 8601 con +00:00."""
    return momento.replace(tzinfo=timezone.utc).isoformat()


def serializar(fila):
    """Convierte el timestamp de una fila a ISO 8601 para la respuesta JSON."""
    if isinstance(fila.get('timestamp'), datetime):
        fila['timestamp'] = a_iso(fila['timestamp'])
    return fila


def leer_timestamp(valor):
    """Devuelve (datetime UTC sin zona, error). Sin valor usa la hora actual."""
    if valor is None:
        return datetime.now(timezone.utc).replace(tzinfo=None), None
    if not isinstance(valor, str):
        return None, 'timestamp debe ser texto ISO 8601'
    try:
        momento = datetime.fromisoformat(valor)
    except ValueError:
        return None, 'timestamp debe tener formato ISO 8601'
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    if momento.year < 1970:
        return None, 'timestamp debe ser posterior a 1970'
    return momento, None


def sensor_existe(sensor_id):
    """True/False según el catálogo de Sensores; None si no se puede comprobar.

    Si Sensores no responde (o la validación está desactivada) no se bloquea la lectura:
    un sensor real no debe perder datos porque el catálogo esté caído.
    """
    if not SENSORES_URL:
        return None
    if not sensor_id.isascii() or not sensor_id.isdigit():
        return False
    try:
        respuesta = requests.get(f'{SENSORES_URL}/sensores/{int(sensor_id)}', timeout=2)
    except requests.exceptions.RequestException:
        return None
    if respuesta.status_code == 404:
        return False
    return True if respuesta.status_code == 200 else None


def error_sensor_desconocido(sensor_id):
    """Respuesta 400 si el sensor no está en el catálogo; None en cualquier otro caso."""
    if sensor_existe(sensor_id) is False:
        return jsonify({'error': f'el sensor {sensor_id} no existe en el catálogo de Sensores'}), 400
    return None


def a_numero(valor):
    """Convierte a float si es un número válido (rechaza booleanos y texto)."""
    if isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def sensor_valido(sensor_id):
    if isinstance(sensor_id, bool) or not isinstance(sensor_id, (int, str)):
        return None
    texto = str(sensor_id).strip()
    if not texto or len(texto) > 50:
        return None
    return texto


def entero_positivo(texto):
    """Convierte texto ASCII a entero >= 1; devuelve None si no es válido."""
    if texto is None or not texto.isascii() or not texto.isdigit() or int(texto) < 1:
        return None
    return int(texto)


def unidad_valida(unidad):
    if unidad is None:
        return None, True
    if isinstance(unidad, str) and len(unidad) <= 10:
        return unidad, True
    return None, False


@app.route('/health', methods=['GET'])
def health_check():
    try:
        with cursor_bd() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except mysql.connector.Error:
        return jsonify({'status': 'error', 'detalle': 'base de datos no disponible'}), 503
    return jsonify({'status': 'ok'}), 200


@app.route('/mediciones', methods=['POST'])
def crear_medicion():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'sensor_id' not in data or 'valor' not in data:
        return jsonify({'error': 'sensor_id y valor son requeridos'}), 400

    sensor_id = sensor_valido(data['sensor_id'])
    valor = a_numero(data['valor'])
    unidad, unidad_ok = unidad_valida(data.get('unidad'))
    if sensor_id is None:
        return jsonify({'error': 'sensor_id no es válido'}), 400
    if valor is None:
        return jsonify({'error': 'valor debe ser numérico'}), 400
    if not unidad_ok:
        return jsonify({'error': 'unidad debe ser texto de máximo 10 caracteres'}), 400
    momento, error = leer_timestamp(data.get('timestamp'))
    if error:
        return jsonify({'error': error}), 400
    desconocido = error_sensor_desconocido(sensor_id)
    if desconocido:
        return desconocido

    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'INSERT INTO mediciones (sensor_id, valor, unidad, timestamp) VALUES (%s, %s, %s, %s)',
            (sensor_id, valor, unidad, momento),
        )
        nuevo_id = cursor.lastrowid

    return jsonify({
        'id': nuevo_id,
        'sensor_id': sensor_id,
        'valor': valor,
        'unidad': unidad,
        'timestamp': a_iso(momento),
    }), 201


def ultimas_mediciones(condiciones, parametros, limite):
    """Las `limite` mediciones más recientes que cumplen las condiciones, en orden cronológico."""
    consulta = 'SELECT * FROM mediciones'
    if condiciones:
        consulta += ' WHERE ' + ' AND '.join(condiciones)
    consulta = f'SELECT * FROM ({consulta} ORDER BY id DESC LIMIT %s) ultimas ORDER BY id'
    with cursor_bd() as cursor:
        cursor.execute(consulta, [*parametros, limite])
        return [serializar(fila) for fila in cursor.fetchall()]


def leer_limite():
    """Lee ?limit= de la petición. Devuelve (limite, error)."""
    if 'limit' not in request.args:
        return LIMITE_POR_DEFECTO, None
    limite = entero_positivo(request.args['limit'])
    if limite is None:
        return None, 'limit debe ser un entero positivo'
    return min(limite, LIMITE_MAXIMO), None


@app.route('/mediciones', methods=['GET'])
def listar_mediciones():
    """Mediciones en orden cronológico. Devuelve como máximo las N más recientes (por defecto 100, tope 1000).

    Filtros: ?sensor_id= , ?id= , ?limit= , ?desde_id= (solo las posteriores a ese id).
    """
    medicion_id = request.args.get('id')
    sensor_id = request.args.get('sensor_id')
    desde_id = request.args.get('desde_id')

    if medicion_id is not None:
        if not medicion_id.isascii() or not medicion_id.isdigit():
            return jsonify({'error': 'id debe ser un entero'}), 400
        return obtener_medicion(int(medicion_id))

    limite, error = leer_limite()
    if error:
        return jsonify({'error': error}), 400

    condiciones, parametros = [], []
    if sensor_id:
        condiciones.append('sensor_id = %s')
        parametros.append(sensor_id)
    if desde_id is not None:
        if not desde_id.isascii() or not desde_id.isdigit():
            return jsonify({'error': 'desde_id debe ser un entero'}), 400
        condiciones.append('id > %s')
        parametros.append(int(desde_id))

    return respuesta_con_limite(ultimas_mediciones(condiciones, parametros, limite), limite)


def respuesta_con_limite(lista, limite):
    """JSON de la lista con la cabecera X-Limite, para que el cliente sepa que la lista está acotada."""
    respuesta = jsonify(lista)
    respuesta.headers['X-Limite'] = str(limite)
    return respuesta, 200


@app.route('/mediciones/estadisticas', methods=['GET'])
def estadisticas():
    """Total, sensores con lecturas y promedio por unidad, calculados en SQL. Filtro opcional: ?sensor_id=.

    No hay un promedio global: mezclaría magnitudes distintas (°C con %). `promedio` solo se
    incluye al filtrar por sensor, cuyas lecturas comparten unidad.
    """
    sensor_id = request.args.get('sensor_id')
    donde, parametros = ('WHERE sensor_id = %s', [sensor_id]) if sensor_id else ('', [])
    with cursor_bd() as cursor:
        cursor.execute(
            "SELECT COALESCE(unidad, '') AS unidad, COUNT(*) AS total, AVG(valor) AS promedio "
            f'FROM mediciones {donde} GROUP BY unidad ORDER BY unidad',
            parametros,
        )
        grupos = cursor.fetchall()
        cursor.execute(f'SELECT DISTINCT sensor_id FROM mediciones {donde} ORDER BY sensor_id', parametros)
        sensores = [fila['sensor_id'] for fila in cursor.fetchall()]

    total = sum(g['total'] for g in grupos)
    resultado = {
        'total': total,
        'sensores': sensores,
        'por_unidad': [
            {'unidad': g['unidad'], 'total': g['total'], 'promedio': round(float(g['promedio']), 2)}
            for g in grupos
        ],
    }
    if sensor_id:
        # Promedio ponderado de los grupos = promedio de todas las lecturas del sensor.
        suma = sum(float(g['promedio']) * g['total'] for g in grupos)
        resultado['promedio'] = round(suma / total, 2) if total else None
    return jsonify(resultado), 200


@app.route('/mediciones/<int:medicion_id>', methods=['GET'])
def obtener_medicion(medicion_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM mediciones WHERE id = %s', (medicion_id,))
        fila = cursor.fetchone()
    if not fila:
        return jsonify({'error': 'medicion no encontrada'}), 404
    return jsonify(serializar(fila)), 200


@app.route('/mediciones/sensor/<sensor_id>', methods=['GET'])
def obtener_mediciones_por_sensor(sensor_id):
    limite, error = leer_limite()
    if error:
        return jsonify({'error': error}), 400
    return respuesta_con_limite(ultimas_mediciones(['sensor_id = %s'], [sensor_id], limite), limite)


@app.route('/mediciones/<int:medicion_id>', methods=['PUT'])
def reemplazar_medicion(medicion_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'sensor_id' not in data or 'valor' not in data:
        return jsonify({'error': 'sensor_id y valor son requeridos'}), 400

    sensor_id = sensor_valido(data['sensor_id'])
    valor = a_numero(data['valor'])
    unidad, unidad_ok = unidad_valida(data.get('unidad'))
    if sensor_id is None:
        return jsonify({'error': 'sensor_id no es válido'}), 400
    if valor is None:
        return jsonify({'error': 'valor debe ser numérico'}), 400
    if not unidad_ok:
        return jsonify({'error': 'unidad debe ser texto de máximo 10 caracteres'}), 400
    desconocido = error_sensor_desconocido(sensor_id)
    if desconocido:
        return desconocido

    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'UPDATE mediciones SET sensor_id = %s, valor = %s, unidad = %s WHERE id = %s',
            (sensor_id, valor, unidad, medicion_id),
        )
        encontrada = cursor.rowcount > 0
    if not encontrada:
        return jsonify({'error': 'medicion no encontrada'}), 404

    return jsonify({
        'mensaje': 'medicion actualizada correctamente',
        'id': medicion_id,
        'sensor_id': sensor_id,
        'valor': valor,
        'unidad': unidad,
    }), 200


@app.route('/mediciones/<int:medicion_id>', methods=['PATCH'])
def actualizar_medicion(medicion_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or ('valor' not in data and 'unidad' not in data):
        return jsonify({'error': 'valor o unidad es requerido'}), 400

    campos, parametros, respuesta = [], [], {'id': medicion_id}
    if 'valor' in data:
        valor = a_numero(data['valor'])
        if valor is None:
            return jsonify({'error': 'valor debe ser numérico'}), 400
        campos.append('valor = %s')
        parametros.append(valor)
        respuesta['valor'] = valor
    if 'unidad' in data:
        unidad, unidad_ok = unidad_valida(data['unidad'])
        if not unidad_ok:
            return jsonify({'error': 'unidad debe ser texto de máximo 10 caracteres'}), 400
        campos.append('unidad = %s')
        parametros.append(unidad)
        respuesta['unidad'] = unidad

    parametros.append(medicion_id)
    with cursor_bd(commit=True) as cursor:
        cursor.execute(f"UPDATE mediciones SET {', '.join(campos)} WHERE id = %s", parametros)
        encontrada = cursor.rowcount > 0
    if not encontrada:
        return jsonify({'error': 'medicion no encontrada'}), 404

    respuesta['mensaje'] = 'medicion actualizada correctamente'
    return jsonify(respuesta), 200


@app.route('/mediciones/<int:medicion_id>', methods=['DELETE'])
def eliminar_medicion(medicion_id):
    with cursor_bd(commit=True) as cursor:
        cursor.execute('DELETE FROM mediciones WHERE id = %s', (medicion_id,))
        eliminada = cursor.rowcount > 0
    if not eliminada:
        return jsonify({'error': 'medicion no encontrada'}), 404
    return jsonify({'mensaje': 'medicion eliminada correctamente', 'id': medicion_id}), 200


if __name__ == '__main__':
    # Solo para desarrollo local; en el contenedor se ejecuta con gunicorn (ver gunicorn_conf.py).
    if not inicializar():
        sys.exit('[mediciones] no se pudo preparar la base de datos')
    app.run(host='0.0.0.0', port=5001)
