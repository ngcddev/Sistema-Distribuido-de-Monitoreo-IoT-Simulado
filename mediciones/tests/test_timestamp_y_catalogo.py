from contextlib import contextmanager
from datetime import datetime

import mysql.connector
import pytest
import requests

import app as app_module

MOMENTO = datetime(2026, 1, 2, 3, 4, 5)


# ---------------------------------------------------------------- timestamp

def test_leer_timestamp_sin_valor_usa_la_hora_actual():
    momento, error = app_module.leer_timestamp(None)
    assert error is None
    assert momento.tzinfo is None


@pytest.mark.parametrize('texto', [
    '2026-01-02T03:04:05+00:00',
    '2026-01-02T05:04:05+02:00',
    '2026-01-02T03:04:05Z',
    '2026-01-02T03:04:05',
])
def test_leer_timestamp_normaliza_a_utc(texto):
    assert app_module.leer_timestamp(texto) == (MOMENTO, None)


@pytest.mark.parametrize('valor', ['ayer', 123, '1900-01-01T00:00:00', ''])
def test_leer_timestamp_rechaza_invalidos(valor):
    momento, error = app_module.leer_timestamp(valor)
    assert momento is None and error


def test_post_acepta_el_timestamp_del_sensor(cliente, bd):
    respuesta = cliente.post('/mediciones', json={
        'sensor_id': 1, 'valor': 20, 'timestamp': '2026-01-02T05:04:05+02:00'})
    assert respuesta.status_code == 201
    assert respuesta.get_json()['timestamp'] == '2026-01-02T03:04:05+00:00'
    assert bd.consultas[0][1][3] == MOMENTO


def test_post_rechaza_timestamp_invalido(cliente, bd):
    respuesta = cliente.post('/mediciones', json={'sensor_id': 1, 'valor': 20, 'timestamp': 'ayer'})
    assert respuesta.status_code == 400
    assert bd.consultas == []


def test_listar_serializa_el_timestamp_a_iso(cliente, bd):
    bd.filas = [{'id': 1, 'sensor_id': '1', 'valor': 1.0, 'unidad': 'C',
                 'timestamp': datetime(2026, 1, 2, 3, 4, 5, 123000)}]
    assert cliente.get('/mediciones').get_json()[0]['timestamp'] == '2026-01-02T03:04:05.123000+00:00'


def test_obtener_serializa_el_timestamp_a_iso(cliente, bd):
    bd.fila = {'id': 1, 'sensor_id': '1', 'valor': 1.0, 'unidad': 'C', 'timestamp': MOMENTO}
    assert cliente.get('/mediciones/1').get_json()['timestamp'] == '2026-01-02T03:04:05+00:00'


# ---------------------------------------------------------------- validación contra Sensores

class RespuestaFalsa:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.fixture
def catalogo(monkeypatch):
    """Activa la validación y deja que cada test decida qué responde Sensores."""
    monkeypatch.setattr(app_module, 'SENSORES_URL', 'http://sensores:5003')
    estado = {'llamadas': [], 'resultado': RespuestaFalsa(200)}

    def falso(url, timeout):
        estado['llamadas'].append(url)
        if isinstance(estado['resultado'], Exception):
            raise estado['resultado']
        return estado['resultado']

    monkeypatch.setattr(app_module.requests, 'get', falso)
    return estado


def test_post_rechaza_sensor_que_no_existe(cliente, bd, catalogo):
    catalogo['resultado'] = RespuestaFalsa(404)
    respuesta = cliente.post('/mediciones', json={'sensor_id': 99, 'valor': 20})
    assert respuesta.status_code == 400
    assert catalogo['llamadas'] == ['http://sensores:5003/sensores/99']
    assert bd.consultas == []


def test_post_acepta_sensor_del_catalogo(cliente, bd, catalogo):
    assert cliente.post('/mediciones', json={'sensor_id': 1, 'valor': 20}).status_code == 201


def test_post_rechaza_sensor_no_numerico_sin_consultar_sensores(cliente, bd, catalogo):
    assert cliente.post('/mediciones', json={'sensor_id': 'abc', 'valor': 20}).status_code == 400
    assert catalogo['llamadas'] == []


@pytest.mark.parametrize('resultado', [requests.exceptions.ConnectionError(), RespuestaFalsa(500)])
def test_post_no_bloquea_si_sensores_no_responde(cliente, bd, catalogo, resultado):
    catalogo['resultado'] = resultado
    assert cliente.post('/mediciones', json={'sensor_id': 1, 'valor': 20}).status_code == 201


def test_put_tambien_valida_el_sensor(cliente, bd, catalogo):
    catalogo['resultado'] = RespuestaFalsa(404)
    assert cliente.put('/mediciones/1', json={'sensor_id': 99, 'valor': 1}).status_code == 400
    assert bd.consultas == []


def test_sin_sensores_url_no_se_valida(cliente, bd, monkeypatch):
    monkeypatch.setattr(app_module, 'SENSORES_URL', None)
    assert cliente.post('/mediciones', json={'sensor_id': 'cualquiera', 'valor': 20}).status_code == 201


# ---------------------------------------------------------------- errores de base de datos

def falla_con(monkeypatch, error):
    @contextmanager
    def cursor_que_falla(commit=False):
        raise error
        yield  # pragma: no cover

    monkeypatch.setattr(app_module, 'cursor_bd', cursor_que_falla)


@pytest.mark.parametrize('error', [
    mysql.connector.errors.DatabaseError('sin conexión', errno=2003),
    mysql.connector.errors.InterfaceError('sin conexión'),
])
def test_error_de_conexion_da_503(cliente, monkeypatch, error):
    falla_con(monkeypatch, error)
    assert cliente.get('/mediciones/1').status_code == 503


def test_error_de_consulta_da_500_no_503(cliente, monkeypatch):
    falla_con(monkeypatch, mysql.connector.errors.ProgrammingError('sintaxis', errno=1064))
    respuesta = cliente.get('/mediciones/1')
    assert respuesta.status_code == 500
    assert 'conectar' not in respuesta.get_json()['error']
