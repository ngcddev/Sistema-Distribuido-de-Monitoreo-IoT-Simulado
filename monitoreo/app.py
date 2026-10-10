import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

MEDICIONES_URL = os.environ.get('MEDICIONES_URL', 'http://localhost:5001')


UMBRALES_CONFIG = {
    "temperatura": {"unidad": "C", "min": 10.0, "max": 35.0},
    "huedad": {"unidad": "%", "min": 30.0, "max": 80.0}
}


@app.route('/health', methods=['GET'])  # check endpoint para ver si funciona el microservicio
def health_check():
    return jsonify({'status': 'ok'}), 200


@app.route('/monitoreo/umbrales', methods=['GET'])
def obtener_umbrales():
    """Consulta la configuración actual de umbrales para las variables ambientales. """
    return jsonify({
        "descripcion": "umbrales configurado para la generación de alertas en tiempo real",
        "umbrales": UMBRALES_CONFIG
    }), 200


@app.route("/monitoreo/<sensor_id>", methods=["GET"])
def resumen_sensor(sensor_id):
    try:
        respuesta = requests.get(
            f"{MEDICIONES_URL}/mediciones",
            params={"sensor_id": sensor_id},
            timeout=3
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Error al conectar con Mediciones"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "el servicio de Mediciones no respondió a tiempo"}), 503

    if respuesta.status_code != 200:
        return jsonify({"error": "el servicio de mediciones devolvió un error"}), 503

    lecturas = respuesta.json()

    #Filtramos solo las lecturas
    lecturas_sensor = [l for l in lecturas if str(l["sensor_id"]) == str(sensor_id)]

    if not lecturas_sensor:
        return jsonify({"mensaje": f"El sensor {sensor_id} no tieene lecturas todavia"}), 404

    #calculos para alrmar el json
    cantidad = len(lecturas_sensor)
    valores = [float(l["valor"]) for l in lecturas_sensor]
    promedio = round(sum(valores) / cantidad, 2)

    #buscamos la ultima lectura
    ultima = lecturas_sensor[-1]


    return jsonify({
        "sensor_id": str(sensor_id),
        "cantidad_lecturas": cantidad,
        "promedio": promedio,
        "ultima_lectura": ultima
    }), 200


@app.route("/monitoreo/evaluar/<sensor_id>", methods=["GET"])
def evaluar_sensor(sensor_id):
    """Evalúa la última lectura de un sensor frente a los umbrales permitidos."""
    try:
        respuesta = requests.get(
            f"{MEDICIONES_URL}/mediciones",
            params={"sensor_id": sensor_id},
            timeout=3
        )
    except requests.exceptions.RequestException:
        return jsonify({"error": "No se pudo conectar con Mediciones para evaluar"}), 503

    if respuesta.status_code != 200:
        return jsonify({"error": "Error en el servicio de Mediciones"}), 503

    lecturas = respuesta.json()
    lecturas_sensor = [l for l in lecturas if str(l["sensor_id"]) == str(sensor_id)]

    if not lecturas_sensor:
        return jsonify({"mensaje": f"Sin datos para evaluar el sensor {sensor_id}"}), 404

    ultima_lectura = lecturas_sensor[-1]
    valor = float(ultima_lectura["valor"])
    unidad = ultima_lectura.get("unidad", "C")

    # Lógica de evaluación de riesgo
    estado = "NORMAL"
    detalles = "El valor se encuentra dentro del rango operativo seguro."

    if valor > 35.0:
        estado = "ALERTA_CRITICA"
        detalles = f"El valor {valor} {unidad} supera el límite máximo permitido (35.0)."
    elif valor < 10.0:
        estado = "ALERTA_CRITICA"
        detalles = f"El valor {valor} {unidad} está por debajo del límite mínimo permitido (10.0)."

    return jsonify({
        "sensor_id": str(sensor_id),
        "evaluacion": estado,
        "diagnostico": detalles,
        "valor_evaluado": valor,
        "timestamp_evaluado": ultima_lectura.get("timestamp")
    }), 200


@app.route("/monitoreo/resumen-general", methods=["GET"])
def resumen_general():
    """Analiza la totalidad de mediciones de todos los sensores en la red."""
    try:
        respuesta = requests.get(f"{MEDICIONES_URL}/mediciones", timeout=3)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Error al conectar con Mediciones para el reporte general"}), 503

    if respuesta.status_code != 200:
        return jsonify({"error": "No se pudo obtener el historial completo"}), 503

    todas_las_lecturas = respuesta.json()

    if not todas_las_lecturas:
        return jsonify({"mensaje": "No hay lecturas registradas en la red"}), 200

    # Agrupación y procesamiento de métricas globales
    sensores_detectados = list(set(str(l["sensor_id"]) for l in todas_las_lecturas))
    valores_totales = [float(l["valor"]) for l in todas_las_lecturas]
    promedio_global = round(sum(valores_totales) / len(valores_totales), 2)

    return jsonify({
        "total_lecturas_sistema": len(todas_las_lecturas),
        "total_sensores_activos": len(sensores_detectados),
        "listado_sensores": sensores_detectados,
        "promedio_global_sistema": promedio_global
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002) 