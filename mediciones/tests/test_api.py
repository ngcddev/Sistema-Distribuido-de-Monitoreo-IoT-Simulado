import pytest


def test_post_exige_sensor_y_valor(cliente, bd):
    assert cliente.post('/mediciones', json={'sensor_id': 1}).status_code == 400
    assert cliente.post('/mediciones', data='no es json').status_code == 400


@pytest.mark.parametrize('valor', [True, 'abc', None, [1]])
def test_post_rechaza_valores_no_numericos(cliente, bd, valor):
    respuesta = cliente.post('/mediciones', json={'sensor_id': 1, 'valor': valor})
    assert respuesta.status_code == 400
    assert bd.consultas == []


def test_post_rechaza_unidad_larga(cliente, bd):
    respuesta = cliente.post('/mediciones', json={'sensor_id': 1, 'valor': 20, 'unidad': 'x' * 11})
    assert respuesta.status_code == 400


def test_post_crea_medicion(cliente, bd):
    respuesta = cliente.post('/mediciones', json={'sensor_id': 1, 'valor': '21.5', 'unidad': 'C'})
    assert respuesta.status_code == 201
    cuerpo = respuesta.get_json()
    assert cuerpo['id'] == 7
    assert cuerpo['valor'] == 21.5
    assert cuerpo['sensor_id'] == '1'
    assert bd.consultas[0][1][:3] == ('1', 21.5, 'C')


def test_listar_aplica_limite_por_defecto(cliente, bd):
    assert cliente.get('/mediciones').status_code == 200
    sql, parametros = bd.consultas[0]
    assert 'ORDER BY id DESC LIMIT %s' in sql
    assert parametros == [100]


def test_listar_limita_al_maximo(cliente, bd):
    cliente.get('/mediciones?limit=999999')
    assert bd.consultas[0][1] == [1000]


@pytest.mark.parametrize('limite', ['0', '-1', 'abc', '²', ''])
def test_listar_rechaza_limit_invalido(cliente, bd, limite):
    assert cliente.get(f'/mediciones?limit={limite}').status_code == 400


def test_listar_filtra_por_sensor_y_desde_id(cliente, bd):
    cliente.get('/mediciones?sensor_id=3&desde_id=10&limit=5')
    sql, parametros = bd.consultas[0]
    assert 'WHERE sensor_id = %s AND id > %s' in sql
    assert parametros == ['3', 10, 5]


def test_listar_rechaza_desde_id_invalido(cliente, bd):
    assert cliente.get('/mediciones?desde_id=x').status_code == 400


def test_mediciones_por_sensor_tambien_tiene_limite(cliente, bd):
    cliente.get('/mediciones/sensor/2')
    assert bd.consultas[0][1] == ['2', 100]


def test_listar_informa_el_limite_aplicado(cliente, bd):
    assert cliente.get('/mediciones').headers['X-Limite'] == '100'
    assert cliente.get('/mediciones?limit=5').headers['X-Limite'] == '5'
    assert cliente.get('/mediciones/sensor/1').headers['X-Limite'] == '100'


def test_estadisticas_promedia_por_unidad_sin_mezclar(cliente, bd):
    bd.cola_filas = [
        [{'unidad': '%', 'total': 1, 'promedio': 60.0}, {'unidad': 'C', 'total': 3, 'promedio': 20.123}],
        [{'sensor_id': '1'}, {'sensor_id': '3'}],
    ]
    respuesta = cliente.get('/mediciones/estadisticas')
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        'total': 4,
        'sensores': ['1', '3'],
        'por_unidad': [
            {'unidad': '%', 'total': 1, 'promedio': 60.0},
            {'unidad': 'C', 'total': 3, 'promedio': 20.12},
        ],
    }
    assert 'COALESCE(unidad' in bd.consultas[0][0] and 'GROUP BY unidad' in bd.consultas[0][0]


def test_estadisticas_de_un_sensor_incluye_promedio_ponderado(cliente, bd):
    bd.cola_filas = [
        [{'unidad': 'C', 'total': 3, 'promedio': 20.0}, {'unidad': 'F', 'total': 1, 'promedio': 40.0}],
        [{'sensor_id': '1'}],
    ]
    cuerpo = cliente.get('/mediciones/estadisticas?sensor_id=1').get_json()
    assert cuerpo['promedio'] == 25.0
    assert bd.consultas[0][1] == ['1']


def test_estadisticas_sin_datos(cliente, bd):
    bd.cola_filas = [[], []]
    assert cliente.get('/mediciones/estadisticas').get_json() == {'total': 0, 'sensores': [], 'por_unidad': []}
    bd.cola_filas = [[], []]
    assert cliente.get('/mediciones/estadisticas?sensor_id=9').get_json()['promedio'] is None


def test_obtener_inexistente_da_404(cliente, bd):
    bd.fila = None
    assert cliente.get('/mediciones/99').status_code == 404


def test_put_inexistente_da_404(cliente, bd):
    bd.rowcount = 0
    assert cliente.put('/mediciones/99', json={'sensor_id': 1, 'valor': 1}).status_code == 404


def test_patch_exige_un_campo(cliente, bd):
    assert cliente.patch('/mediciones/1', json={}).status_code == 400


def test_delete_inexistente_da_404(cliente, bd):
    bd.rowcount = 0
    assert cliente.delete('/mediciones/99').status_code == 404
