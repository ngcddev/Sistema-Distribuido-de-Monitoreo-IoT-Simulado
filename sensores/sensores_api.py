from flask import Flask 

sensor = Flask(__name__)

@sensor.route('/sensores', methods=["GET"])
def datos_sensor():
    datos = [
        {
            "id":1,
            "tipo":"Ph",
            "ubicacion":"popayan-cauca",
            "estado":"Normal (rango optmimo)"
        },

        {
            "id":2,
            "tipo":"Turbidez",
            "ubicacion":"popayan-cauca",
            "estado":"5 NTU (Unidad nefelometrico de turbidez)"
        },

        {
            "id":3,
            "tipo":"Temperatura",
            "ubicacion":"popayan-cauca",
            "estado":"Temperatura alta"
        }
    ]

    return datos

