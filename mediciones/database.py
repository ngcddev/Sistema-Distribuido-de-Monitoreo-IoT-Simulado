import os
import re
import time

import mysql.connector
from mysql.connector.constants import ClientFlag

TABLA_MEDICIONES = """
CREATE TABLE IF NOT EXISTS mediciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sensor_id VARCHAR(50) NOT NULL,
  valor DOUBLE NOT NULL,
  unidad VARCHAR(10),
  timestamp VARCHAR(40) NOT NULL,
  INDEX idx_sensor (sensor_id)
)
"""


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
    nombre = os.environ.get('DB_NAME', 'mediciones')
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
                cursor.execute(TABLA_MEDICIONES)
                conexion.commit()
                cursor.close()
            finally:
                conexion.close()
            print('[mediciones] base de datos lista')
            return True
        except mysql.connector.Error as err:
            print(f'[mediciones] esperando a MySQL ({intento}/{intentos}): {err}')
            time.sleep(espera)
    return False
