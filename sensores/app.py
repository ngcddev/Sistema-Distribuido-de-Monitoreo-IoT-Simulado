from flask import Flask, jsonify, request

app = Flask(__name__)

sensores_db = []
_next_id = 1

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200


@app.route('/sensores', methods=['GET'])
def listar_sensores():
    return jsonify(sensores_db), 200


@app.route('/sensores/<int:sensor_id>', methods=['GET'])
def obtener_sensor(sensor_id):
    for s in sensores_db:
        if s['id'] == sensor_id:
            return jsonify(s), 200
    return jsonify({'error': 'sensor no encontrado'}), 404


@app.route('/sensores', methods=['POST'])
def crear_sensor():
    global _next_id
    data = request.get_json(silent=True) or {}
    if 'tipo' not in data or 'ubicacion' not in data:
        return jsonify({'error': 'tipo y ubicacion son requeridos'}), 400

    sensor = {
        'id': _next_id,
        'tipo': data['tipo'],
        'ubicacion': data['ubicacion'],
        'activo': True,
    }
    _next_id += 1
    sensores_db.append(sensor)
    return jsonify(sensor), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)