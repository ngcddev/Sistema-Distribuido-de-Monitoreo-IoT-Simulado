"""Evalúa de forma automática las lecturas nuevas contra los umbrales y registra las alertas.

Corre como un proceso aparte (servicio `evaluador` en compose.yaml), reutilizando la
lógica de app.py. Parte desde la última lectura existente al arrancar y, en cada ciclo,
evalúa solo las lecturas posteriores.

También aplica la retención a las alertas: cada hora borra las anteriores a RETENCION_DIAS
(las lecturas las purga el servicio `purgador` de Mediciones).
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import mysql.connector
import requests

from app import MedicionesNoDisponible, consultar_mediciones, cursor_bd, evaluar_lectura

logger = logging.getLogger('evaluador')

INTERVALO_SEGUNDOS = int(os.environ.get('INTERVALO_EVALUACION_SEGUNDOS', 10))
RETENCION_DIAS = int(os.environ.get('RETENCION_DIAS', 30))
INTERVALO_PURGA_SEGUNDOS = 3600
LOTE_MAXIMO = 1000
LOTE_PURGA = 10000


def ultimo_id_existente():
    lecturas = consultar_mediciones(limit=1)
    return lecturas[-1]['id'] if lecturas else 0


def evaluar_nuevas(ultimo_id):
    """Evalúa las lecturas con id > ultimo_id y devuelve el id más alto procesado."""
    for lectura in consultar_mediciones(desde_id=ultimo_id, limit=LOTE_MAXIMO):
        evaluar_lectura(lectura['sensor_id'], lectura)
        ultimo_id = max(ultimo_id, lectura['id'])
    return ultimo_id


def purgar_alertas(dias, lote=LOTE_PURGA, ahora=None):
    """Borra las alertas anteriores al límite de retención y devuelve cuántas borró."""
    ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
    limite = ahora - timedelta(days=dias)
    total = 0
    while True:
        with cursor_bd(commit=True) as cursor:
            cursor.execute('DELETE FROM alertas WHERE timestamp < %s LIMIT %s', (limite, lote))
            borradas = cursor.rowcount
        total += borradas
        if borradas < lote:
            return total


def main():
    logger.info('iniciando…')
    ultimo_id = None
    while ultimo_id is None:
        try:
            ultimo_id = ultimo_id_existente()
        except MedicionesNoDisponible as err:
            logger.warning('esperando a Mediciones: %s', err)
            time.sleep(INTERVALO_SEGUNDOS)

    logger.info('evaluando lecturas nuevas (id > %s) cada %ss', ultimo_id, INTERVALO_SEGUNDOS)
    if RETENCION_DIAS > 0:
        logger.info('conservando las alertas de los últimos %s días', RETENCION_DIAS)
    proxima_purga = 0.0
    while True:
        try:
            ultimo_id = evaluar_nuevas(ultimo_id)
        except (MedicionesNoDisponible, mysql.connector.Error, requests.exceptions.RequestException) as err:
            # Se reintenta en el siguiente ciclo desde la última lectura procesada.
            logger.warning('ciclo con error: %s', err)

        if RETENCION_DIAS > 0 and time.monotonic() >= proxima_purga:
            proxima_purga = time.monotonic() + INTERVALO_PURGA_SEGUNDOS
            try:
                borradas = purgar_alertas(RETENCION_DIAS)
                if borradas:
                    logger.info('borradas %s alertas con más de %s días', borradas, RETENCION_DIAS)
            except mysql.connector.Error as err:
                logger.warning('no se pudo purgar alertas: %s', err)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
