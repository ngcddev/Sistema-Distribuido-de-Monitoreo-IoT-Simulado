import os
import re
import time

import mysql.connector
from mysql.connector.constants import ClientFlag

TABLA_SENSORES = """
CREATE TABLE IF NOT EXISTS sensores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  tipo VARCHAR(30) NOT NULL,
  ubicacion VARCHAR(80),
  activo TINYINT(1) NOT NULL DEFAULT 1
)
"""

SENSORES_INICIALES = [
    (1, "Temperatura sala", "temperatura", "sala"),
    (2, "Temperatura cocina", "temperatura", "cocina"),
    (3, "Humedad invernadero", "humedad", "invernadero"),
]


def _parametros(con_bd=True):
    parametros = {
        'host': os.environ.get('DB_HOST'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        # rowcount cuenta filas encontradas, no solo modificadas (evita 404 falsos en UPDATE)
        'client_flags': [ClientFlag.FOUND_ROWS],
        'connection_timeout': 5,
    }
    if con_bd:
        parametros['database'] = os.environ.get('DB_NAME')
    return parametros


def conectar():
    return mysql.connector.connect(**_parametros())


def inicializar(intentos=30, espera=2):
    """Crea la base de datos y la tabla si no existen; reintenta mientras MySQL arranca."""
    nombre = os.environ.get('DB_NAME', 'sensores')
    if not re.fullmatch(r'[A-Za-z0-9_]+', nombre):
        raise ValueError('DB_NAME no es un identificador válido')

    for intento in range(1, intentos + 1):
        try:
            conexion = mysql.connector.connect(**_parametros(con_bd=False))
            try:
                cursor = conexion.cursor()
                try:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{nombre}`")
                except mysql.connector.Error:
                    pass  # sin permiso de CREATE: se asume que la BD ya existe
                cursor.execute(f"USE `{nombre}`")
                cursor.execute(TABLA_SENSORES)
                cursor.execute("SELECT COUNT(*) FROM sensores")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        "INSERT INTO sensores (id, nombre, tipo, ubicacion) VALUES (%s, %s, %s, %s)",
                        SENSORES_INICIALES,
                    )
                conexion.commit()
                cursor.close()
            finally:
                conexion.close()
            print('[sensores] base de datos lista')
            return True
        except mysql.connector.Error as err:
            print(f'[sensores] esperando a MySQL ({intento}/{intentos}): {err}')
            time.sleep(espera)
    return False
