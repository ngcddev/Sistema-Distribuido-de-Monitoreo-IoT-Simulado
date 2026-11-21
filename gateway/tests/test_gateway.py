"""El Gateway reenvía método, query, cuerpo y código de estado, y traduce los fallos de comunicación."""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as gateway  # noqa: E402


class RespuestaFalsa:
    def __init__(self, estado=200, contenido=b'{"ok": true}'):
        self.status_code = estado
        self.content = contenido
        self.headers = {'Content-Type': 'application/json'}


@pytest.fixture
def cliente(monkeypatch):
    gateway.app.config['TESTING'] = True
    return gateway.app.test_client()


@pytest.fixture
def enviadas(monkeypatch):
    """Registra las solicitudes que el Gateway reenvía a los servicios."""
    registro = []

    def solicitud(metodo, url, **kwargs):
        registro.append({'metodo': metodo, 'url': url, **kwargs})
        return RespuestaFalsa()

    monkeypatch.setattr(gateway.requests, 'request', solicitud)
    return registro


@pytest.mark.parametrize('ruta, destino', [
    ('/sensores', 'http://sensores:5003/sensores'),
    ('/sensores/4', 'http://sensores:5003/sensores/4'),
    ('/mediciones', 'http://mediciones:5001/mediciones'),
    ('/mediciones/sensor/2', 'http://mediciones:5001/mediciones/sensor/2'),
    ('/mediciones/estadisticas', 'http://mediciones:5001/mediciones/estadisticas'),
    ('/monitoreo/umbrales', 'http://monitoreo:5002/monitoreo/umbrales'),
    ('/monitoreo/alertas/3', 'http://monitoreo:5002/monitoreo/alertas/3'),
    ('/monitoreo/resumen-general', 'http://monitoreo:5002/monitoreo/resumen-general'),
    ('/monitoreo/circuitos', 'http://monitoreo:5002/monitoreo/circuitos'),
])
def test_cada_ruta_llega_a_su_servicio(cliente, enviadas, ruta, destino):
    assert cliente.get(ruta).status_code == 200
    assert enviadas[0]['url'] == destino


def test_reenvia_query_cuerpo_y_metodo(cliente, enviadas):
    cliente.put('/mediciones/7?x=1', data='{"valor": 3}', content_type='application/json')
    pedido = enviadas[0]
    assert pedido['metodo'] == 'PUT'
    assert pedido['params']['x'] == '1'
    assert pedido['data'] == b'{"valor": 3}'
    assert pedido['headers']['Content-Type'] == 'application/json'


def test_no_reenvia_cabeceras_de_autorizacion(cliente, enviadas):
    cliente.delete('/sensores/1', headers={'Authorization': 'Basic eDp5'})
    assert 'Authorization' not in enviadas[0]['headers']


def test_conserva_codigo_y_cuerpo_del_servicio(cliente, monkeypatch):
    monkeypatch.setattr(gateway.requests, 'request',
                        lambda *a, **k: RespuestaFalsa(404, b'{"error": "sensor no encontrado"}'))
    respuesta = cliente.get('/sensores/99')
    assert respuesta.status_code == 404
    assert respuesta.get_json() == {'error': 'sensor no encontrado'}


def test_timeout_responde_504(cliente, monkeypatch):
    def lento(*_a, **_k):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(gateway.requests, 'request', lento)
    respuesta = cliente.get('/mediciones')
    assert respuesta.status_code == 504
    assert 'mediciones' in respuesta.get_json()['error']


def test_servicio_caido_responde_503(cliente, monkeypatch):
    def caido(*_a, **_k):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(gateway.requests, 'request', caido)
    assert cliente.get('/sensores').status_code == 503


def test_ruta_desconocida_responde_404_json(cliente):
    respuesta = cliente.get('/otro')
    assert respuesta.status_code == 404
    assert 'error' in respuesta.get_json()


def test_metodo_no_permitido_responde_405_json(cliente):
    respuesta = cliente.open('/sensores', method='TRACE')
    assert respuesta.status_code == 405
    assert 'error' in respuesta.get_json()


def test_evaluar_se_reenvia(cliente, enviadas):
    assert cliente.get('/monitoreo/evaluar/1').status_code == 200
    assert enviadas[0]['url'] == 'http://monitoreo:5002/monitoreo/evaluar/1'


def test_health_informa_el_estado_de_cada_servicio(cliente, monkeypatch):
    def get(url, **_k):
        if 'sensores' in url:
            raise requests.exceptions.ConnectionError()
        return RespuestaFalsa()

    monkeypatch.setattr(gateway.requests, 'get', get)
    datos = cliente.get('/health').get_json()
    assert datos['servicios'] == {'sensores': 'no disponible', 'mediciones': 'ok', 'monitoreo': 'ok'}
