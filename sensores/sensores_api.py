from flask import Flask, request

sensor = Flask(__name__)

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
@sensor.route('/sensores', methods=["GET"])
def datos_sensor():
    if not datos: 
        return {"mensaje":"No hay datos"}
    return datos


@sensor.route("/sensores/<id>", methods=["GET"])
def datos_sensor_id(id: int):

    for i  in datos:
        if i['id']== int(id):
            return {
                "id":i["id"],
                "tipo": i["tipo"],
                "ubicacion": i["ubicacion"],
                "estado": i["estado"]
            }, 200
        
    if not datos:
        return {"mensaje":"No hay datos"}, 404
    
    
    return {"mensaje":f"El usuario con el id {id}, no existe"}, 404



@sensor.route("/sensores", methods=["POST"])
def registrar_datos():
    mayor = 0
    valores = request.get_json()
    for i in datos:
        if i["id"] > mayor:
            mayor = i["id"]
    valores["id"] = mayor + 1
    datos.append(valores)
    return valores, 201



if __name__ == "__main__":
    sensor.run(host="0.0.0.0", port=5000, debug=True)