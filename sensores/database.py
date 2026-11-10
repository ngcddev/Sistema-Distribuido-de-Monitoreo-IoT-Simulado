import logging
import os
import re
import time

import mysql.connector
from mysql.connector.constants import ClientFlag

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger('sensores')

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
        parametros['database'] = os.environ.get('DB_NAME', 'sensores')
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
                except mysql.connector.Error as err:
                    # Sin permiso de CREATE se asume que la BD ya existe (MySQL la crea con MYSQL_DATABASE).
                    logger.debug('CREATE DATABASE omitido: %s', err)
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
            logger.info('base de datos lista')
            return True
        except mysql.connector.Error as err:
            logger.warning('esperando a MySQL (%s/%s): %s', intento, intentos, err)
            time.sleep(espera)
    return False
