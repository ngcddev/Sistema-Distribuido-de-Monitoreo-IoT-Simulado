import os
import re
import time

import mysql.connector
from mysql.connector.constants import ClientFlag

TABLAS = [
    """
    CREATE TABLE IF NOT EXISTS umbrales (
      id INT AUTO_INCREMENT PRIMARY KEY,
      tipo VARCHAR(30) NOT NULL UNIQUE,
      minimo DOUBLE NOT NULL,
      maximo DOUBLE NOT NULL,
      unidad VARCHAR(10)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alertas (
      id INT AUTO_INCREMENT PRIMARY KEY,
      medicion_id INT NOT NULL UNIQUE,
      sensor_id VARCHAR(50) NOT NULL,
      tipo VARCHAR(30),
      valor DOUBLE NOT NULL,
      estado VARCHAR(30) NOT NULL,
      detalle VARCHAR(255),
      timestamp VARCHAR(40),
      INDEX idx_sensor (sensor_id)
    )
    """,
]

UMBRALES_INICIALES = [
    ("temperatura", 10.0, 35.0, "C"),
    ("humedad", 30.0, 80.0, "%"),
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
        parametros['database'] = os.environ.get('DB_NAME', 'monitoreo')
    return parametros


def conectar():
    return mysql.connector.connect(**_parametros())


def inicializar(intentos=30, espera=2):
    """Crea la base de datos y la tabla si no existen; reintenta mientras MySQL arranca."""
    nombre = os.environ.get('DB_NAME', 'monitoreo')
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
                for tabla in TABLAS:
                    cursor.execute(tabla)
                cursor.execute("SELECT COUNT(*) FROM umbrales")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        "INSERT INTO umbrales (tipo, minimo, maximo, unidad) VALUES (%s, %s, %s, %s)",
                        UMBRALES_INICIALES,
                    )
                conexion.commit()
                cursor.close()
            finally:
                conexion.close()
            print('[monitoreo] base de datos lista')
            return True
        except mysql.connector.Error as err:
            print(f'[monitoreo] esperando a MySQL ({intento}/{intentos}): {err}')
            time.sleep(espera)
    return False
