"""Evalúa de forma automática las lecturas nuevas contra los umbrales y registra las alertas.

Corre como un proceso aparte (servicio `evaluador` en compose.yaml), reutilizando la
lógica de app.py. Parte desde la última lectura existente al arrancar y, en cada ciclo,
evalúa solo las lecturas posteriores.
"""
import logging
import os
import sys
import time

import mysql.connector
import requests

from app import MedicionesNoDisponible, consultar_mediciones, evaluar_lectura

logger = logging.getLogger('evaluador')

INTERVALO_SEGUNDOS = int(os.environ.get('INTERVALO_EVALUACION_SEGUNDOS', 10))
LOTE_MAXIMO = 1000


def ultimo_id_existente():
    lecturas = consultar_mediciones(limit=1)
    return lecturas[-1]['id'] if lecturas else 0


def evaluar_nuevas(ultimo_id):
    """Evalúa las lecturas con id > ultimo_id y devuelve el id más alto procesado."""
    for lectura in consultar_mediciones(desde_id=ultimo_id, limit=LOTE_MAXIMO):
        evaluar_lectura(lectura['sensor_id'], lectura)
        ultimo_id = max(ultimo_id, lectura['id'])
    return ultimo_id


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
    while True:
        try:
            ultimo_id = evaluar_nuevas(ultimo_id)
        except (MedicionesNoDisponible, mysql.connector.Error, requests.exceptions.RequestException) as err:
            # Se reintenta en el siguiente ciclo desde la última lectura procesada.
            logger.warning('ciclo con error: %s', err)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
