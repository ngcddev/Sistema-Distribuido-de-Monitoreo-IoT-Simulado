import pytest

FILA = {'id': 4, 'nombre': 'Humedad', 'tipo': 'humedad', 'ubicacion': 'sala', 'activo': 1}


def test_listar_serializa_activo_como_booleano(cliente, bd):
    bd.filas = [dict(FILA)]
    assert cliente.get('/sensores').get_json()[0]['activo'] is True


def test_listar_filtra_por_tipo_y_activo(cliente, bd):
    cliente.get('/sensores?tipo=humedad&activo=false')
    sql, parametros = bd.consultas[0]
    assert 'WHERE tipo = %s AND activo = %s' in sql
    assert parametros == ['humedad', 0]


def test_listar_rechaza_activo_invalido(cliente, bd):
    assert cliente.get('/sensores?activo=quizas').status_code == 400


def test_obtener_inexistente_da_404(cliente, bd):
    bd.fila = None
    assert cliente.get('/sensores/99').status_code == 404


@pytest.mark.parametrize('datos', [
    {'nombre': 'x'},
    {'tipo': 'humedad'},
    {'nombre': '', 'tipo': 'humedad'},
    {'nombre': 'x' * 81, 'tipo': 'humedad'},
    {'nombre': 'x', 'tipo': 'presion'},
    {'nombre': 'x', 'tipo': 'humedad', 'activo': 'si'},
    {'nombre': 'x', 'tipo': 'humedad', 'ubicacion': 'y' * 81},
])
def test_crear_rechaza_datos_invalidos(cliente, bd, datos):
    assert cliente.post('/sensores', json=datos).status_code == 400
    assert bd.consultas == []


def test_crear_sensor(cliente, bd):
    bd.fila = dict(FILA)
    respuesta = cliente.post('/sensores', json={'nombre': 'Humedad', 'tipo': 'humedad'})
    assert respuesta.status_code == 201
    assert bd.consultas[0][1] == ('Humedad', 'humedad', None, 1)


def test_actualizar_inexistente_da_404(cliente, bd):
    bd.rowcount = 0
    assert cliente.put('/sensores/99', json={'nombre': 'x', 'tipo': 'humedad'}).status_code == 404


def test_eliminar_inexistente_da_404(cliente, bd):
    bd.rowcount = 0
    assert cliente.delete('/sensores/99').status_code == 404
