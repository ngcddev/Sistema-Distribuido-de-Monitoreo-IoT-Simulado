from contextlib import contextmanager
from datetime import datetime

import mysql.connector
import pytest

import purga


class Detener(Exception):
    """Corta el bucle infinito de main() en las pruebas."""


class CursorFalso:
    """Devuelve, en cada DELETE, el siguiente número de filas borradas de la lista."""

    def __init__(self, borradas):
        self.borradas = list(borradas)
        self.consultas = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))
        self.rowcount = self.borradas.pop(0)


@pytest.fixture
def instalar(monkeypatch):
    def _instalar(borradas):
        cursor = CursorFalso(borradas)

        @contextmanager
        def cursor_falso(commit=False):
            assert commit, 'el borrado debe confirmarse'
            yield cursor

        monkeypatch.setattr(purga, 'cursor_bd', cursor_falso)
        return cursor
    return _instalar


def test_limite_de_retencion_resta_los_dias():
    assert purga.limite_de_retencion(30, ahora=datetime(2026, 3, 31, 12)) == datetime(2026, 3, 1, 12)


def test_purgar_borra_por_lotes_hasta_que_un_lote_sale_incompleto(instalar):
    cursor = instalar([10, 10, 3])
    total = purga.purgar(30, lote=10, ahora=datetime(2026, 3, 31))
    assert total == 23
    assert len(cursor.consultas) == 3
    sql, parametros = cursor.consultas[0]
    assert sql == 'DELETE FROM mediciones WHERE timestamp < %s LIMIT %s'
    assert parametros == (datetime(2026, 3, 1), 10)


def test_purgar_sin_nada_que_borrar_hace_una_sola_consulta(instalar):
    cursor = instalar([0])
    assert purga.purgar(30) == 0
    assert len(cursor.consultas) == 1


def test_con_retencion_desactivada_no_se_borra_nada(instalar, monkeypatch):
    cursor = instalar([])
    monkeypatch.setattr(purga, 'RETENCION_DIAS', 0)

    def dormir(segundos):
        raise Detener

    monkeypatch.setattr(purga.time, 'sleep', dormir)
    with pytest.raises(Detener):
        purga.main()
    assert cursor.consultas == []


def test_main_purga_cada_ciclo(monkeypatch):
    llamadas = []
    monkeypatch.setattr(purga, 'RETENCION_DIAS', 7)
    monkeypatch.setattr(purga, 'purgar', lambda dias: llamadas.append(dias) or 5)

    def dormir(segundos):
        if len(llamadas) >= 2:
            raise Detener

    monkeypatch.setattr(purga.time, 'sleep', dormir)
    with pytest.raises(Detener):
        purga.main()
    assert llamadas == [7, 7]


def test_main_sigue_vivo_si_la_base_de_datos_falla(monkeypatch):
    intentos = []

    def purgar_con_fallo(dias):
        intentos.append(dias)
        if len(intentos) == 1:
            raise mysql.connector.errors.DatabaseError('sin conexión', errno=2003)
        return 0

    monkeypatch.setattr(purga, 'RETENCION_DIAS', 30)
    monkeypatch.setattr(purga, 'purgar', purgar_con_fallo)

    def dormir(segundos):
        if len(intentos) >= 2:
            raise Detener

    monkeypatch.setattr(purga.time, 'sleep', dormir)
    with pytest.raises(Detener):
        purga.main()
    assert len(intentos) == 2
