from contextlib import contextmanager
from datetime import datetime, timezone

import mysql.connector
from flask import Flask, jsonify, request

from database import conectar, inicializar

app = Flask(__name__)

LIMITE_MAXIMO = 1000


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
def error_base_datos(_err):
    return jsonify({'error': 'no se pudo conectar con la base de datos'}), 503


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

    timestamp = datetime.now(timezone.utc).isoformat()
    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'INSERT INTO mediciones (sensor_id, valor, unidad, timestamp) VALUES (%s, %s, %s, %s)',
            (sensor_id, valor, unidad, timestamp),
        )
        nuevo_id = cursor.lastrowid

    return jsonify({
        'id': nuevo_id,
        'sensor_id': sensor_id,
        'valor': valor,
        'unidad': unidad,
        'timestamp': timestamp,
    }), 201


@app.route('/mediciones', methods=['GET'])
def listar_mediciones():
    """Lista mediciones en orden cronológico. Filtros: ?sensor_id= , ?id= , ?limit= (las N más recientes)."""
    medicion_id = request.args.get('id')
    sensor_id = request.args.get('sensor_id')
    limite = request.args.get('limit')

    if medicion_id is not None:
        if not medicion_id.isdigit():
            return jsonify({'error': 'id debe ser un entero'}), 400
        return obtener_medicion(int(medicion_id))

    if limite is not None:
        if not limite.isdigit() or int(limite) < 1:
            return jsonify({'error': 'limit debe ser un entero positivo'}), 400
        limite = min(int(limite), LIMITE_MAXIMO)

    consulta = 'SELECT * FROM mediciones'
    parametros = []
    if sensor_id:
        consulta += ' WHERE sensor_id = %s'
        parametros.append(sensor_id)

    if limite:
        consulta = f'SELECT * FROM ({consulta} ORDER BY id DESC LIMIT %s) ultimas ORDER BY id'
        parametros.append(limite)
    else:
        consulta += ' ORDER BY id'

    with cursor_bd() as cursor:
        cursor.execute(consulta, parametros)
        resultado = cursor.fetchall()
    return jsonify(resultado), 200


@app.route('/mediciones/<int:medicion_id>', methods=['GET'])
def obtener_medicion(medicion_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM mediciones WHERE id = %s', (medicion_id,))
        fila = cursor.fetchone()
    if not fila:
        return jsonify({'error': 'medicion no encontrada'}), 404
    return jsonify(fila), 200


@app.route('/mediciones/sensor/<sensor_id>', methods=['GET'])
def obtener_mediciones_por_sensor(sensor_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM mediciones WHERE sensor_id = %s ORDER BY id', (sensor_id,))
        resultado = cursor.fetchall()
    return jsonify(resultado), 200


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
    inicializar()
    app.run(host='0.0.0.0', port=5001)
