from contextlib import contextmanager

import mysql.connector
from flask import Flask, jsonify, request

from database import conectar, inicializar

app = Flask(__name__)

TIPOS_VALIDOS = ('temperatura', 'humedad')


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


def serializar(fila):
    fila['activo'] = bool(fila['activo'])
    return fila


def validar(data, completo):
    """Devuelve (campos, error). Si completo=True exige nombre y tipo."""
    if not isinstance(data, dict):
        return None, 'se esperaba un objeto JSON'

    campos = {}
    if completo and ('nombre' not in data or 'tipo' not in data):
        return None, 'nombre y tipo son requeridos'

    if 'nombre' in data:
        nombre = data['nombre']
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 80:
            return None, 'nombre debe ser texto de 1 a 80 caracteres'
        campos['nombre'] = nombre.strip()
    if 'tipo' in data:
        if data['tipo'] not in TIPOS_VALIDOS:
            return None, 'tipo debe ser uno de: ' + ', '.join(TIPOS_VALIDOS)
        campos['tipo'] = data['tipo']
    if 'ubicacion' in data:
        ubicacion = data['ubicacion']
        if ubicacion is not None and (not isinstance(ubicacion, str) or len(ubicacion) > 80):
            return None, 'ubicacion debe ser texto de máximo 80 caracteres'
        campos['ubicacion'] = ubicacion
    if 'activo' in data:
        if not isinstance(data['activo'], bool):
            return None, 'activo debe ser booleano'
        campos['activo'] = int(data['activo'])
    return campos, None


@app.route('/health', methods=['GET'])
def health_check():
    try:
        with cursor_bd() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except mysql.connector.Error:
        return jsonify({'status': 'error', 'detalle': 'base de datos no disponible'}), 503
    return jsonify({'status': 'ok'}), 200


@app.route('/sensores', methods=['GET'])
def listar_sensores():
    """Filtros opcionales: ?tipo=temperatura  ?activo=true|false"""
    condiciones, parametros = [], []
    tipo = request.args.get('tipo')
    activo = request.args.get('activo')
    if tipo:
        condiciones.append('tipo = %s')
        parametros.append(tipo)
    if activo is not None:
        if activo.lower() not in ('true', 'false'):
            return jsonify({'error': 'activo debe ser true o false'}), 400
        condiciones.append('activo = %s')
        parametros.append(1 if activo.lower() == 'true' else 0)

    consulta = 'SELECT * FROM sensores'
    if condiciones:
        consulta += ' WHERE ' + ' AND '.join(condiciones)
    consulta += ' ORDER BY id'

    with cursor_bd() as cursor:
        cursor.execute(consulta, parametros)
        filas = cursor.fetchall()
    return jsonify([serializar(f) for f in filas]), 200


@app.route('/sensores/<int:sensor_id>', methods=['GET'])
def obtener_sensor(sensor_id):
    with cursor_bd() as cursor:
        cursor.execute('SELECT * FROM sensores WHERE id = %s', (sensor_id,))
        fila = cursor.fetchone()
    if not fila:
        return jsonify({'error': 'sensor no encontrado'}), 404
    return jsonify(serializar(fila)), 200


@app.route('/sensores', methods=['POST'])
def crear_sensor():
    campos, error = validar(request.get_json(silent=True), completo=True)
    if error:
        return jsonify({'error': error}), 400

    campos.setdefault('ubicacion', None)
    campos.setdefault('activo', 1)
    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'INSERT INTO sensores (nombre, tipo, ubicacion, activo) VALUES (%s, %s, %s, %s)',
            (campos['nombre'], campos['tipo'], campos['ubicacion'], campos['activo']),
        )
        nuevo_id = cursor.lastrowid
        cursor.execute('SELECT * FROM sensores WHERE id = %s', (nuevo_id,))
        fila = cursor.fetchone()
    return jsonify(serializar(fila)), 201


@app.route('/sensores/<int:sensor_id>', methods=['PUT'])
def actualizar_sensor(sensor_id):
    campos, error = validar(request.get_json(silent=True), completo=True)
    if error:
        return jsonify({'error': error}), 400

    campos.setdefault('ubicacion', None)
    campos.setdefault('activo', 1)
    with cursor_bd(commit=True) as cursor:
        cursor.execute(
            'UPDATE sensores SET nombre = %s, tipo = %s, ubicacion = %s, activo = %s WHERE id = %s',
            (campos['nombre'], campos['tipo'], campos['ubicacion'], campos['activo'], sensor_id),
        )
        if cursor.rowcount == 0:
            return jsonify({'error': 'sensor no encontrado'}), 404
        cursor.execute('SELECT * FROM sensores WHERE id = %s', (sensor_id,))
        fila = cursor.fetchone()
    return jsonify(serializar(fila)), 200


@app.route('/sensores/<int:sensor_id>', methods=['DELETE'])
def eliminar_sensor(sensor_id):
    with cursor_bd(commit=True) as cursor:
        cursor.execute('DELETE FROM sensores WHERE id = %s', (sensor_id,))
        eliminado = cursor.rowcount > 0
    if not eliminado:
        return jsonify({'error': 'sensor no encontrado'}), 404
    return jsonify({'mensaje': 'sensor eliminado correctamente', 'id': sensor_id}), 200


if __name__ == '__main__':
    inicializar()
    app.run(host='0.0.0.0', port=5003)
