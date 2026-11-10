import re
from pathlib import Path

import database

SQL = Path(__file__).resolve().parents[2] / 'bases_datos' / 'mediciones.sql'


def normalizar(texto):
    return re.sub(r'\s+|`', '', texto).lower()


def test_database_py_coincide_con_el_script_de_referencia():
    """bases_datos/mediciones.sql es documentación: no debe desincronizarse de database.py."""
    assert normalizar(database.TABLA_MEDICIONES) in normalizar(SQL.read_text(encoding='utf-8'))
