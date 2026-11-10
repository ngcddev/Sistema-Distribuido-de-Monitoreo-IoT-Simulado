import re
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
import pytest

import app as app_module
import database

SQL = Path(__file__).resolve().parents[2] / 'bases_datos' / 'sensores.sql'


def normalizar(texto):
    return re.sub(r'\s+|`', '', texto).lower()


def test_database_py_coincide_con_el_script_de_referencia():
    """bases_datos/sensores.sql es documentación: no debe desincronizarse de database.py."""
    assert normalizar(database.TABLA_SENSORES) in normalizar(SQL.read_text(encoding='utf-8'))


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
    assert cliente.get('/sensores/1').status_code == 503


def test_error_de_consulta_da_500_no_503(cliente, monkeypatch):
    falla_con(monkeypatch, mysql.connector.errors.ProgrammingError('sintaxis', errno=1064))
    assert cliente.get('/sensores/1').status_code == 500
