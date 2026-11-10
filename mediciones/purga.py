"""Borra las lecturas más antiguas que RETENCION_DIAS para que la tabla no crezca sin límite.

Corre como un proceso aparte (servicio `purgador` en compose.yaml), reutilizando la conexión de app.py.
Revisa cada hora y borra por lotes pequeños, para no bloquear la tabla mientras entran lecturas nuevas.
"""
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import mysql.connector

from app import cursor_bd

logger = logging.getLogger('purgador')

RETENCION_DIAS = int(os.environ.get('RETENCION_DIAS', 30))
INTERVALO_SEGUNDOS = int(os.environ.get('PURGA_INTERVALO_SEGUNDOS', 3600))
LOTE = 10000


def limite_de_retencion(dias, ahora=None):
    """Fecha (UTC, sin zona, como se guarda en MySQL) anterior a la cual las lecturas se descartan."""
    ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
    return ahora - timedelta(days=dias)


def purgar(dias, lote=LOTE, ahora=None):
    """Borra las lecturas anteriores al límite de retención y devuelve cuántas borró."""
    limite = limite_de_retencion(dias, ahora)
    total = 0
    while True:
        with cursor_bd(commit=True) as cursor:
            cursor.execute('DELETE FROM mediciones WHERE timestamp < %s LIMIT %s', (limite, lote))
            borradas = cursor.rowcount
        total += borradas
        if borradas < lote:
            return total


def main():
    if RETENCION_DIAS <= 0:
        logger.info('retención desactivada (RETENCION_DIAS=%s): no se borra nada', RETENCION_DIAS)
        while True:
            time.sleep(3600)

    logger.info('conservando las lecturas de los últimos %s días; revisión cada %ss', RETENCION_DIAS, INTERVALO_SEGUNDOS)
    while True:
        try:
            borradas = purgar(RETENCION_DIAS)
            if borradas:
                logger.info('borradas %s lecturas con más de %s días', borradas, RETENCION_DIAS)
        except mysql.connector.Error as err:
            logger.warning('ciclo con error: %s', err)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
