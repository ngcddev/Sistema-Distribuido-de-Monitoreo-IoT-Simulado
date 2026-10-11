from flask import Flask, jsonify, request
from datetime import datetime, timezone
import mysql.connector
from database import conectar

app = Flask(__name__)


@app.route('/health', methods=['GET'])  # check endpoint para ver si funciona el microservicio
def health_check():
    return jsonify({'status': 'ok'}), 200


@app.route('/mediciones', methods=['POST']) # endpoint para crear mediciones
def crear_mediciones():

    data = request.get_json(silent=True)

    if not data or "sensor_id" not in data or "valor" not in data:
        return jsonify({"error":"sensor_id y valor son requeridos"}),  400

    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor(dictionary=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO mediciones (sensor_id, valor, unidad, timestamp) VALUES (%s, %s, %s, %s)
            """
        valores = (data["sensor_id"], data["valor"], data.get("unidad"), timestamp)

        cursor.execute(sql, valores)
        conexion.commit()
        nuevo_id = cursor.lastrowid
        cursor.close()

        return jsonify({
        "id": nuevo_id,
        "sensor_id": data["sensor_id"],
        "valor": data["valor"],
        "unidad": data.get("unidad"),
        "timestamp": timestamp
        }), 201
    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()


@app.route('/mediciones', methods=['GET']) # endpoint para obtener mediciones, con opción de filtrar por sensor_id
def obtener_mediciones():
    conexion = None
    try:
        conexion = conectar()
        medicion_id = request.args.get('id')
        sensor_id = request.args.get('sensor_id')

        cursor = conexion.cursor(dictionary=True)
        if medicion_id:
            cursor.execute("SELECT * FROM mediciones WHERE id = %s", (medicion_id,))
            fila = cursor.fetchone()
            cursor.close()
            if not fila:
                return jsonify({"error": "medicion no encontrada"}), 404
            return jsonify(fila), 200
        if sensor_id:
            cursor.execute("SELECT * FROM mediciones WHERE sensor_id = %s", (sensor_id,))
        else:
            cursor.execute("SELECT * FROM mediciones")
        resultado = cursor.fetchall()

        cursor.close()
        return jsonify(resultado), 200
    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()


@app.route('/mediciones/<sensor_id>', methods=['GET']) # endpoint para obtener mediciones de un sensor específico
def obtener_mediciones_por_sensor(sensor_id):
    conexion = None
    try:
        conexion = conectar()

        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mediciones WHERE sensor_id = %s", (sensor_id,))
        resultado = cursor.fetchall()
        cursor.close()

        return jsonify(resultado), 200
    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()

@app.route("/mediciones/<int:medicion_id>", methods=["PUT"])
def actualizar_medicion(medicion_id):
    data = request.get_json()
    if not data or "sensor_id" not in data or "valor" not in data:
        return jsonify({"error": "sensor_id y valor son requeridos"}), 400
    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor(dictionary=True)
        sql = """ UPDATE mediciones SET sensor_id = %s, valor = %s, unidad = %s WHERE id = %s """

        valores = (data["sensor_id"], data["valor"], data.get("unidad"), medicion_id)
        cursor.execute(sql, valores)
        conexion.commit()
        fila_actualizada = cursor.rowcount
        cursor.close()
        if fila_actualizada == 0:
            return jsonify({"error": "medicion no encontrada"}), 404

        return jsonify({
            "mensaje": "medicion actualizada correctamente",
            "id": medicion_id,
            "sensor_id": data["sensor_id"],
            "valor": data["valor"],
            "unidad": data.get("unidad")
        }), 200
    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()

@app.route("/mediciones/<int:medicion_id>", methods=["DELETE"])
def eliminar_medicion(medicion_id):
    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor(dictionary=True)
        sql = """ DELETE FROM mediciones WHERE id = %s """
        valores = (medicion_id,)
        cursor.execute(sql, valores)
        conexion.commit()
        fila_eliminada = cursor.rowcount
        cursor.close()
        if fila_eliminada == 0:
            return jsonify({"error": "medicion no encontrada"}), 404

        return jsonify({
            "mensaje": "medicion eliminada correctamente",
            "id": medicion_id
        }), 200
    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()

@app.route("/mediciones/<int:medicion_id>", methods=["PATCH"])
def actualizar_medicion_parcial(medicion_id):
    data = request.get_json()
    if not data or "valor" not in data:
        return jsonify({"error":"valor es requerido"}), 400
    conexion = None
    try:
        conexion = conectar()
        cursor  = conexion.cursor(dictionary=True)
        sql = """ UPDATE  mediciones SET valor = %s WHERE id = %s """
        valores = (data["valor"], medicion_id)
        cursor.execute(sql, valores)
        conexion.commit()
        fila_actualizada = cursor.rowcount
        cursor.close()
        if fila_actualizada == 0:
            return jsonify({"error": "medicion no encontrada"}), 404
        return jsonify({
            "mensaje": "medicion actualizada correctamente",
            "id": medicion_id,
            "valor": data["valor"]
        }), 200

    except mysql.connector.Error:
        return jsonify({"error": "no se pudo conectar con la base de datos"}), 503
    finally:
        if conexion is not None:
            conexion.close()

if __name__ == "__main__":
     app.run(host="0.0.0.0", port=5001) # cambiar a host="0.0.0.0" para poder dockerizar
