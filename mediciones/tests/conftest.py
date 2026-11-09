from contextlib import contextmanager

import pytest

import app as app_module


class CursorFalso:
    """Cursor en memoria: registra las consultas y devuelve lo que el test configure."""

    def __init__(self):
        self.consultas = []
        self.filas = []
        self.cola_filas = []  # si tiene elementos, cada fetchall() devuelve el siguiente
        self.fila = None
        self.rowcount = 1
        self.lastrowid = 7

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))

    def fetchall(self):
        return self.cola_filas.pop(0) if self.cola_filas else self.filas

    def fetchone(self):
        return self.fila


@pytest.fixture
def bd(monkeypatch):
    cursor = CursorFalso()

    @contextmanager
    def cursor_falso(commit=False):
        yield cursor

    monkeypatch.setattr(app_module, 'cursor_bd', cursor_falso)
    return cursor


@pytest.fixture
def cliente():
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()
