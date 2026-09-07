from flask import Flask, jsonify, request
from datetime import datetime, timezone

app = Flask(__name__)

mediciones_db = []

@app.route('/health', methods=['GET'])  # check endpoint para ver si funciona el microservicio
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route('/mediciones', methods=['POST']) # endpoint para crear mediciones
def crear_mediciones():
    data = request.get_json(silent=True)

    if not data or 'sensor_id' not in data or 'valor' not in data:
        return jsonify({'error': 'sensor_id y valor son requeridos'}), 400

    medicion = {
        "sensor_id": data['sensor_id'],
        "valor": data['valor'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    mediciones_db.append(medicion)

    return jsonify(medicion), 201

@app.route('/mediciones', methods=['GET']) # endpoint para obtener mediciones, con opción de filtrar por sensor_id
def obtener_mediciones():
    sensor_id = request.args.get('sensor_id')

    if sensor_id:
        resultado = [m for m in mediciones_db if m['sensor_id'] == sensor_id]
    else:
        resultado = mediciones_db

    return jsonify(resultado), 200

if __name__ == "__main__":
    app.run(host="localhost", port=5001) 