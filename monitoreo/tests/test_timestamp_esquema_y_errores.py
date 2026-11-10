import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import mysql.connector
import pytest

import app as app_module
import database

SQL = Path(__file__).resolve().parents[2] / 'bases_datos' / 'monitoreo.sql'
UMBRAL = {'tipo': 'temperatura', 'minimo': 10.0, 'maximo': 35.0}


def normalizar(texto):
    return re.sub(r'\s+|`', '', texto).lower()


def test_database_py_coincide_con_el_script_de_referencia():
    """bases_datos/monitoreo.sql es documentación: no debe desincronizarse de database.py."""
    sql = normalizar(SQL.read_text(encoding='utf-8'))
    for tabla in database.TABLAS:
        assert normalizar(tabla) in sql


@pytest.mark.parametrize('texto, esperado', [
    ('2026-01-02T03:04:05+00:00', datetime(2026, 1, 2, 3, 4, 5)),
    ('2026-01-02T05:04:05+02:00', datetime(2026, 1, 2, 3, 4, 5)),
    ('2026-01-02T03:04:05.123000+00:00', datetime(2026, 1, 2, 3, 4, 5, 123000)),
    ('basura', None),
    ('', None),
    (None, None),
])
def test_a_datetime_utc(texto, esperado):
    assert app_module.a_datetime_utc(texto) == esperado


def test_evaluar_guarda_el_timestamp_de_la_alerta_como_datetime(bd, monkeypatch):
    monkeypatch.setattr(app_module, 'tipo_de_sensor', lambda sensor_id, lectura: 'temperatura')
    bd.fila = UMBRAL
    lectura = {'id': 5, 'valor': 40, 'unidad': 'C', 'timestamp': '2026-01-02T03:04:05+00:00'}
    app_module.evaluar_lectura(1, lectura)
    insercion = [c for c in bd.consultas if c[0].startswith('INSERT IGNORE INTO alertas')][0]
    assert insercion[1][-1] == datetime(2026, 1, 2, 3, 4, 5)


def test_listar_alertas_serializa_el_timestamp_a_iso(cliente, bd):
    bd.filas = [{'id': 1, 'sensor_id': '1', 'timestamp': datetime(2026, 1, 2, 3, 4, 5)}]
    assert cliente.get('/monitoreo/alertas').get_json()[0]['timestamp'] == '2026-01-02T03:04:05+00:00'


@pytest.mark.parametrize('limite', ['0', 'abc', '²', ''])
def test_listar_alertas_rechaza_limit_invalido(cliente, bd, limite):
    assert cliente.get(f'/monitoreo/alertas?limit={limite}').status_code == 400


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
    assert cliente.get('/monitoreo/umbrales').status_code == 503


def test_error_de_consulta_da_500_no_503(cliente, monkeypatch):
    falla_con(monkeypatch, mysql.connector.errors.ProgrammingError('sintaxis', errno=1064))
    assert cliente.get('/monitoreo/umbrales').status_code == 500


def test_umbral_duplicado_sigue_dando_409(cliente, monkeypatch):
    falla_con(monkeypatch, mysql.connector.errors.IntegrityError('duplicado', errno=1062))
    respuesta = cliente.post('/monitoreo/umbrales', json={'tipo': 'x', 'minimo': 1, 'maximo': 2})
    assert respuesta.status_code == 409
