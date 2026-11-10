import pytest
import requests

import app as app_module


class RespuestaFalsa:
    def __init__(self, status_code=200, datos=None, texto=''):
        self.status_code = status_code
        self._datos = datos
        self.text = texto

    def json(self):
        if self._datos is None:
            raise ValueError('sin JSON')
        return self._datos


class SesionFalsa:
    """Sustituye a requests.Session: guarda las llamadas y responde lo que el test indique."""

    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas = []

    def _atender(self, metodo, url, **kwargs):
        self.llamadas.append((metodo, url, kwargs))
        if self.error:
            raise self.error
        return self.respuesta

    def get(self, url, **kwargs):
        return self._atender('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self._atender('POST', url, **kwargs)


@pytest.fixture
def sesion(monkeypatch):
    def instalar(respuesta=None, error=None):
        falsa = SesionFalsa(respuesta, error)
        monkeypatch.setattr(app_module, 'sesion', falsa)
        return falsa
    return instalar


# ---------------------------------------------------------------- generar_valor

@pytest.mark.parametrize('tipo, unidad, rango', [
    ('temperatura', 'C', (15, 40)),
    ('humedad', '%', (20, 100)),
])
def test_generar_valor_respeta_rango_y_unidad(tipo, unidad, rango):
    for _ in range(200):
        valor, u = app_module.generar_valor(tipo)
        assert rango[0] <= valor <= rango[1]
        assert u == unidad


def test_generar_valor_de_tipo_desconocido_usa_temperatura():
    valor, unidad = app_module.generar_valor('presion')
    assert unidad == 'C'
    assert 15 <= valor <= 40


# ---------------------------------------------------------------- cargar_sensores

def test_cargar_sensores_usa_el_catalogo(sesion):
    catalogo = [{'id': 7, 'tipo': 'humedad', 'ubicacion': 'huerto'}]
    falsa = sesion(RespuestaFalsa(200, catalogo))
    assert app_module.cargar_sensores() == catalogo
    assert falsa.llamadas[0][2]['params'] == {'activo': 'true'}


@pytest.mark.parametrize('respuesta', [
    RespuestaFalsa(200, []),
    RespuestaFalsa(500, {'error': 'x'}),
    RespuestaFalsa(200, None),
])
def test_cargar_sensores_usa_el_respaldo_si_no_hay_catalogo_util(sesion, respuesta):
    sesion(respuesta)
    assert app_module.cargar_sensores() == app_module.SENSORES_RESPALDO


def test_cargar_sensores_usa_el_respaldo_si_sensores_no_responde(sesion):
    sesion(error=requests.exceptions.ConnectionError('caído'))
    assert app_module.cargar_sensores() == app_module.SENSORES_RESPALDO


# ---------------------------------------------------------------- enviar_medicion

def test_enviar_medicion_hace_post_con_sensor_valor_y_unidad(sesion):
    falsa = sesion(RespuestaFalsa(201))
    app_module.enviar_medicion({'id': 3, 'tipo': 'humedad'})
    metodo, url, kwargs = falsa.llamadas[0]
    assert (metodo, url) == ('POST', f'{app_module.MEDICIONES_URL}/mediciones')
    assert kwargs['json']['sensor_id'] == 3
    assert kwargs['json']['unidad'] == '%'
    assert 20 <= kwargs['json']['valor'] <= 100


def test_enviar_medicion_no_falla_si_mediciones_rechaza_o_no_responde(sesion):
    sesion(RespuestaFalsa(400, texto='sensor inexistente'))
    app_module.enviar_medicion({'id': 1, 'tipo': 'temperatura'})
    sesion(error=requests.exceptions.ConnectionError('caído'))
    app_module.enviar_medicion({'id': 1, 'tipo': 'temperatura'})


# ---------------------------------------------------------------- esperar_servicio / main

def test_esperar_servicio_responde_a_la_primera(sesion, monkeypatch):
    monkeypatch.setattr(app_module.time, 'sleep', lambda s: pytest.fail('no debía esperar'))
    sesion(RespuestaFalsa(200))
    assert app_module.esperar_servicio('http://x', 'mediciones') is True


def test_esperar_servicio_se_rinde_tras_los_intentos(sesion, monkeypatch):
    esperas = []
    monkeypatch.setattr(app_module.time, 'sleep', esperas.append)
    falsa = sesion(error=requests.exceptions.ConnectionError('caído'))
    assert app_module.esperar_servicio('http://x', 'mediciones', intentos=3, espera=2) is False
    assert len(falsa.llamadas) == 3
    assert esperas == [2, 2, 2]


def test_main_termina_con_error_si_mediciones_no_responde(monkeypatch):
    monkeypatch.setattr(app_module, 'esperar_servicio', lambda *a, **k: False)
    with pytest.raises(SystemExit) as salida:
        app_module.main()
    assert salida.value.code == 1
