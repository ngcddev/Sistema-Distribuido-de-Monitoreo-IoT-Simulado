"""Timeout (504), Circuit Breaker (CLOSED -> OPEN -> HALF_OPEN -> CLOSED) y errores JSON de Monitoreo."""
import os
import sys
import time
from pathlib import Path

import pytest
import requests

os.environ.setdefault('MEDICIONES_URL', 'http://mediciones:5001')
os.environ.setdefault('SENSORES_URL', 'http://sensores:5003')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module  # noqa: E402


class RespuestaFalsa:
    def __init__(self, estado=200, datos=None):
        self.status_code = estado
        self._datos = datos if datos is not None else []

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f'HTTP {self.status_code}')


@pytest.fixture(autouse=True)
def circuito_nuevo(monkeypatch):
    """Cada prueba parte con un circuito CLOSED, umbral de 3 fallas y recuperación de 0.2 s."""
    monkeypatch.setattr(app_module, 'circuito_mediciones', app_module.crear_circuito(
        'mediciones', fail_max=3, reset_timeout=0.2))
    monkeypatch.setattr(app_module, 'circuito_sensores', app_module.crear_circuito(
        'sensores', fail_max=3, reset_timeout=0.2))


@pytest.fixture
def cliente():
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def fallar(monkeypatch, error):
    def get(*_args, **_kwargs):
        raise error
    monkeypatch.setattr(app_module.requests, 'get', get)


def test_timeout_responde_504(cliente, monkeypatch):
    fallar(monkeypatch, requests.exceptions.Timeout())
    respuesta = cliente.get('/monitoreo/resumen-general')
    assert respuesta.status_code == 504
    assert 'a tiempo' in respuesta.get_json()['error']


def test_el_timeout_configurado_se_usa_en_la_llamada(cliente, monkeypatch):
    usados = {}

    def get(url, params=None, timeout=None):
        usados['timeout'] = timeout
        return RespuestaFalsa(datos=[])

    monkeypatch.setattr(app_module.requests, 'get', get)
    cliente.get('/monitoreo/resumen-general')
    assert usados['timeout'] == app_module.MEDICIONES_TIMEOUT


def test_sin_conexion_responde_503(cliente, monkeypatch):
    fallar(monkeypatch, requests.exceptions.ConnectionError())
    assert cliente.get('/monitoreo/resumen-general').status_code == 503


def test_un_5xx_de_mediciones_responde_502_y_cuenta_como_falla(cliente, monkeypatch):
    monkeypatch.setattr(app_module.requests, 'get', lambda *a, **k: RespuestaFalsa(500))
    assert cliente.get('/monitoreo/resumen-general').status_code == 502
    assert app_module.circuito_mediciones.fail_counter == 1


def test_un_404_de_mediciones_no_cuenta_como_falla(cliente, monkeypatch):
    monkeypatch.setattr(app_module.requests, 'get', lambda *a, **k: RespuestaFalsa(404))
    assert cliente.get('/monitoreo/resumen-general').status_code == 404
    assert app_module.circuito_mediciones.fail_counter == 0
    assert app_module.circuito_mediciones.current_state == 'closed'


def test_circuito_closed_open_half_open_closed(cliente, monkeypatch):
    circuito = app_module.circuito_mediciones
    assert app_module.estado_visible(circuito) == 'CLOSED'

    # Fallas técnicas: el contador sube y, al llegar al umbral, el circuito se abre.
    fallar(monkeypatch, requests.exceptions.ConnectionError())
    for esperado in (1, 2):
        assert cliente.get('/monitoreo/resumen-general').status_code == 503
        assert circuito.fail_counter == esperado
        assert app_module.estado_visible(circuito) == 'CLOSED'
    assert cliente.get('/monitoreo/resumen-general').status_code == 503
    assert app_module.estado_visible(circuito) == 'OPEN'

    # OPEN: rechaza sin llamar a Mediciones, aunque ya se haya recuperado.
    llamadas = []

    def get_sano(*_args, **_kwargs):
        llamadas.append(1)
        return RespuestaFalsa(datos=[])

    monkeypatch.setattr(app_module.requests, 'get', get_sano)
    respuesta = cliente.get('/monitoreo/resumen-general')
    assert respuesta.status_code == 503
    assert 'circuito abierto' in respuesta.get_json()['error']
    assert llamadas == []

    # Pasado el tiempo de recuperación: HALF_OPEN deja pasar una solicitud de prueba.
    time.sleep(0.3)
    assert app_module.estado_visible(circuito) == 'HALF_OPEN'
    assert cliente.get('/monitoreo/circuitos').get_json()['mediciones']['estado'] == 'HALF_OPEN'
    assert cliente.get('/monitoreo/resumen-general').status_code == 200
    assert llamadas == [1]
    assert app_module.estado_visible(circuito) == 'CLOSED'


def test_si_la_prueba_de_half_open_falla_vuelve_a_open(cliente, monkeypatch):
    circuito = app_module.circuito_mediciones
    fallar(monkeypatch, requests.exceptions.ConnectionError())
    for _ in range(3):
        cliente.get('/monitoreo/resumen-general')
    time.sleep(0.3)
    assert app_module.estado_visible(circuito) == 'HALF_OPEN'
    cliente.get('/monitoreo/resumen-general')
    assert app_module.estado_visible(circuito) == 'OPEN'


def test_endpoint_de_circuitos(cliente):
    datos = cliente.get('/monitoreo/circuitos').get_json()
    assert datos['mediciones']['estado'] == 'CLOSED'
    assert datos['mediciones']['fallos_maximos'] == 3
    assert {'contador_fallos', 'tiempo_reinicio'} <= set(datos['mediciones'])
    assert set(datos) == {'mediciones', 'sensores'}


def test_sensores_caido_devuelve_advertencia_y_respaldo(monkeypatch):
    fallar(monkeypatch, requests.exceptions.ConnectionError())
    tipo, advertencia = app_module.tipo_de_sensor(1, {'unidad': 'C'})
    assert tipo is None
    assert 'unidad de la lectura' in advertencia


def test_rutas_inexistentes_y_metodos_no_permitidos_responden_json(cliente):
    respuesta = cliente.get('/no-existe/nada/mas')
    assert respuesta.status_code == 404
    assert respuesta.get_json()['error']
    assert cliente.post('/monitoreo/circuitos').status_code == 405


def test_un_error_no_previsto_responde_500_json(cliente, monkeypatch):
    def explota(*_args, **_kwargs):
        raise RuntimeError('fallo inesperado')

    monkeypatch.setattr(app_module, 'consultar_mediciones', explota)
    respuesta = cliente.get('/monitoreo/resumen-general')
    assert respuesta.status_code == 500
    assert respuesta.get_json() == {'error': 'error interno del servidor'}
