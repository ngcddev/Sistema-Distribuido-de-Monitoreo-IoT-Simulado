import pytest

import app as app_module

UMBRAL_TEMPERATURA = {'tipo': 'temperatura', 'minimo': 10.0, 'maximo': 35.0}


@pytest.mark.parametrize('valor, estado', [
    (36.0, 'ALERTA_CRITICA'),
    (9.9, 'ALERTA_CRITICA'),
    (35.0, 'NORMAL'),
    (10.0, 'NORMAL'),
    (22.0, 'NORMAL'),
])
def test_clasificar_con_umbral(valor, estado):
    resultado, detalle = app_module.clasificar(valor, 'C', 'temperatura', UMBRAL_TEMPERATURA)
    assert resultado == estado
    assert detalle


def test_clasificar_sin_umbral():
    estado, detalle = app_module.clasificar(20.0, 'C', 'presion', None)
    assert estado == 'SIN_UMBRAL'
    assert 'presion' in detalle


@pytest.fixture
def sensor_de_temperatura(monkeypatch):
    monkeypatch.setattr(app_module, 'tipo_de_sensor', lambda sensor_id, lectura: 'temperatura')


def test_evaluar_lectura_registra_alerta_fuera_de_rango(bd, sensor_de_temperatura):
    bd.fila = UMBRAL_TEMPERATURA
    lectura = {'id': 5, 'valor': 40, 'unidad': 'C', 'timestamp': 't'}
    resultado = app_module.evaluar_lectura(1, lectura)
    assert resultado['evaluacion'] == 'ALERTA_CRITICA'
    inserciones = [c for c in bd.consultas if c[0].startswith('INSERT IGNORE INTO alertas')]
    assert len(inserciones) == 1
    assert inserciones[0][1][0] == 5


def test_evaluar_lectura_normal_no_registra_alerta(bd, sensor_de_temperatura):
    bd.fila = UMBRAL_TEMPERATURA
    resultado = app_module.evaluar_lectura(1, {'id': 5, 'valor': 20, 'unidad': 'C'})
    assert resultado['evaluacion'] == 'NORMAL'
    assert not [c for c in bd.consultas if c[0].startswith('INSERT')]


def test_evaluar_lectura_sin_registrar_no_escribe(bd, sensor_de_temperatura):
    bd.fila = UMBRAL_TEMPERATURA
    resultado = app_module.evaluar_lectura(1, {'id': 5, 'valor': 40, 'unidad': 'C'}, registrar=False)
    assert resultado['evaluacion'] == 'ALERTA_CRITICA'
    assert resultado['alerta_registrada'] is False
    assert not [c for c in bd.consultas if c[0].startswith('INSERT')]


def test_evaluar_get_solo_consulta(cliente, bd, sensor_de_temperatura, monkeypatch):
    """Compatibilidad: GET sigue respondiendo la evaluación, pero sin registrar la alerta."""
    bd.fila = UMBRAL_TEMPERATURA
    monkeypatch.setattr(app_module, 'consultar_mediciones',
                        lambda *a, **k: [{'id': 1, 'valor': 50, 'unidad': 'C'}])
    respuesta = cliente.get('/monitoreo/evaluar/1')
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo['evaluacion'] == 'ALERTA_CRITICA'
    assert cuerpo['alerta_registrada'] is False
    assert not [c for c in bd.consultas if c[0].startswith('INSERT')]


def test_evaluar_sin_lecturas_da_404(cliente, monkeypatch):
    monkeypatch.setattr(app_module, 'consultar_mediciones', lambda *a, **k: [])
    assert cliente.post('/monitoreo/evaluar/1').status_code == 404


def test_evaluar_post_devuelve_evaluacion(cliente, bd, sensor_de_temperatura, monkeypatch):
    bd.fila = UMBRAL_TEMPERATURA
    monkeypatch.setattr(app_module, 'consultar_mediciones',
                        lambda *a, **k: [{'id': 1, 'valor': 50, 'unidad': 'C'}])
    respuesta = cliente.post('/monitoreo/evaluar/1')
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo['evaluacion'] == 'ALERTA_CRITICA'
    assert cuerpo['alerta_registrada'] is True
    assert [c for c in bd.consultas if c[0].startswith('INSERT IGNORE INTO alertas')]


def test_resumen_general_usa_estadisticas(cliente, monkeypatch):
    llamadas = []

    def falso(ruta='/mediciones', **params):
        llamadas.append((ruta, params))
        return {
            'total': 6,
            'sensores': [1, 2, 3],
            'por_unidad': [
                {'unidad': '%', 'total': 2, 'promedio': 60.0},
                {'unidad': 'C', 'total': 4, 'promedio': 21.5},
                {'unidad': '', 'total': 0, 'promedio': 1.0},
            ],
        }

    monkeypatch.setattr(app_module, 'consultar_mediciones', falso)
    respuesta = cliente.get('/monitoreo/resumen-general')
    assert respuesta.get_json() == {
        'total_lecturas_sistema': 6,
        'total_sensores_activos': 3,
        'listado_sensores': ['1', '2', '3'],
        'promedios_por_unidad': {'%': 60.0, 'C': 21.5, 'sin unidad': 1.0},
    }
    assert llamadas == [('/mediciones/estadisticas', {})]


def test_resumen_general_sin_lecturas(cliente, monkeypatch):
    monkeypatch.setattr(app_module, 'consultar_mediciones',
                        lambda *a, **k: {'total': 0, 'sensores': [], 'por_unidad': []})
    assert 'mensaje' in cliente.get('/monitoreo/resumen-general').get_json()


def test_resumen_sensor(cliente, monkeypatch):
    def falso(ruta='/mediciones', **params):
        if ruta == '/mediciones/estadisticas':
            return {'total': 3, 'promedio': 20.0, 'sensores': ['1']}
        return [{'id': 9, 'valor': 22.0}]

    monkeypatch.setattr(app_module, 'consultar_mediciones', falso)
    cuerpo = cliente.get('/monitoreo/1').get_json()
    assert cuerpo['cantidad_lecturas'] == 3
    assert cuerpo['ultima_lectura']['id'] == 9


def test_resumen_sensor_sin_lecturas_da_404(cliente, monkeypatch):
    monkeypatch.setattr(app_module, 'consultar_mediciones',
                        lambda *a, **k: {'total': 0, 'promedio': None, 'sensores': [], 'por_unidad': []})
    assert cliente.get('/monitoreo/9').status_code == 404


@pytest.mark.parametrize('datos', [
    None,
    {'tipo': 'temperatura', 'minimo': 1},
    {'tipo': '', 'minimo': 1, 'maximo': 2},
    {'tipo': 'x', 'minimo': 'a', 'maximo': 2},
    {'tipo': 'x', 'minimo': 5, 'maximo': 5},
    {'tipo': 'x', 'minimo': 1, 'maximo': 2, 'unidad': 'x' * 11},
])
def test_validar_umbral_rechaza(datos):
    umbral, error = app_module.validar_umbral(datos)
    assert umbral is None and error


def test_validar_umbral_normaliza_el_tipo():
    umbral, error = app_module.validar_umbral({'tipo': ' Temperatura ', 'minimo': 1, 'maximo': 2})
    assert error is None
    assert umbral['tipo'] == 'temperatura'
