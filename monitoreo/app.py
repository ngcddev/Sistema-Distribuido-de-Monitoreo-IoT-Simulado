import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001/mediciones')

@app.route('/health', methods=['GET'])  # check endpoint para ver si funciona el microservicio
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route("/monitoreo/<sensor_id>", methods=["GET"])
def resumen_sensor(sensor_id):
    try:
        respuesta = requests.get(
            f"{MEDICIONES_URL}/mediciones",
            params={"sensor_id": sensor_id},
            timeout=3
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "no se pudo conectar con el servicio de mediciones"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "el servicio de mediciones no respondió a tiempo"}), 503

    if respuesta.status_code != 200:
        return jsonify({"error": "el servicio de mediciones devolvió un error"}), 503

    lecturas = respuesta.json()

    if not lecturas:
        return jsonify({
            "sensor_id": sensor_id,
            "cantidad_lecturas": 0,
            "promedio": None,
            "ultima_lectura": None
        }), 200

    valores = [l["valor"] for l in lecturas]
    promedio = sum(valores) / len(valores)
    ultima = max(lecturas, key=lambda l: l["timestamp"])

    return jsonify({
        "sensor_id": sensor_id,
        "cantidad_lecturas": len(lecturas),
        "promedio": round(promedio, 2),
        "ultima_lectura": ultima
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002) 