from contextlib import contextmanager
from datetime import datetime

import pytest

import worker
from app import MedicionesNoDisponible


class Detener(Exception):
    """Corta el bucle infinito de main() en las pruebas."""


class CursorFalso:
    def __init__(self, borradas):
        self.borradas = list(borradas)
        self.consultas = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))
        self.rowcount = self.borradas.pop(0)


@pytest.fixture
def instalar_cursor(monkeypatch):
    def _instalar(borradas):
        cursor = CursorFalso(borradas)

        @contextmanager
        def cursor_falso(commit=False):
            assert commit, 'el borrado debe confirmarse'
            yield cursor

        monkeypatch.setattr(worker, 'cursor_bd', cursor_falso)
        return cursor
    return _instalar


# ---------------------------------------------------------------- evaluar_nuevas

def test_evaluar_nuevas_evalua_cada_lectura_y_devuelve_el_id_mas_alto(monkeypatch):
    evaluadas = []
    monkeypatch.setattr(worker, 'consultar_mediciones',
                        lambda **params: [{'id': 5, 'sensor_id': '1'}, {'id': 7, 'sensor_id': '2'}])
    monkeypatch.setattr(worker, 'evaluar_lectura', lambda sensor_id, lectura: evaluadas.append((sensor_id, lectura['id'])))
    assert worker.evaluar_nuevas(4) == 7
    assert evaluadas == [('1', 5), ('2', 7)]


def test_evaluar_nuevas_sin_lecturas_conserva_el_id(monkeypatch):
    monkeypatch.setattr(worker, 'consultar_mediciones', lambda **params: [])
    assert worker.evaluar_nuevas(9) == 9


def test_evaluar_nuevas_pide_solo_las_posteriores(monkeypatch):
    pedidos = []
    monkeypatch.setattr(worker, 'consultar_mediciones', lambda **params: pedidos.append(params) or [])
    worker.evaluar_nuevas(12)
    assert pedidos == [{'desde_id': 12, 'limit': worker.LOTE_MAXIMO}]


# ---------------------------------------------------------------- purgar_alertas

def test_purgar_alertas_borra_por_lotes(instalar_cursor):
    cursor = instalar_cursor([10, 4])
    total = worker.purgar_alertas(30, lote=10, ahora=datetime(2026, 3, 31))
    assert total == 14
    assert len(cursor.consultas) == 2
    sql, parametros = cursor.consultas[0]
    assert sql == 'DELETE FROM alertas WHERE timestamp < %s LIMIT %s'
    assert parametros == (datetime(2026, 3, 1), 10)


# ---------------------------------------------------------------- main

def preparar_main(monkeypatch, retencion, ciclos):
    """Arranca main() con todo simulado y la corta tras `ciclos` esperas."""
    purgas = []
    esperas = []
    monkeypatch.setattr(worker, 'RETENCION_DIAS', retencion)
    monkeypatch.setattr(worker, 'ultimo_id_existente', lambda: 3)
    monkeypatch.setattr(worker, 'evaluar_nuevas', lambda ultimo_id: ultimo_id)
    monkeypatch.setattr(worker, 'purgar_alertas', lambda dias: purgas.append(dias) or 2)
    monkeypatch.setattr(worker.time, 'monotonic', lambda: 1000.0)

    def dormir(segundos):
        esperas.append(segundos)
        if len(esperas) >= ciclos:
            raise Detener

    monkeypatch.setattr(worker.time, 'sleep', dormir)
    return purgas, esperas


def test_main_purga_alertas_una_vez_por_hora_aunque_el_ciclo_sea_corto(monkeypatch):
    purgas, _ = preparar_main(monkeypatch, retencion=30, ciclos=3)
    with pytest.raises(Detener):
        worker.main()
    assert purgas == [30]  # 3 ciclos seguidos, una sola purga


def test_main_no_purga_alertas_si_la_retencion_esta_desactivada(monkeypatch):
    purgas, _ = preparar_main(monkeypatch, retencion=0, ciclos=2)
    with pytest.raises(Detener):
        worker.main()
    assert purgas == []


def test_main_espera_a_que_mediciones_este_disponible(monkeypatch):
    purgas, esperas = preparar_main(monkeypatch, retencion=0, ciclos=3)
    intentos = []

    def ultimo_id():
        intentos.append(1)
        if len(intentos) == 1:
            raise MedicionesNoDisponible('caído')
        return 4

    monkeypatch.setattr(worker, 'ultimo_id_existente', ultimo_id)
    with pytest.raises(Detener):
        worker.main()
    assert len(intentos) == 2
    assert esperas[0] == worker.INTERVALO_SEGUNDOS
