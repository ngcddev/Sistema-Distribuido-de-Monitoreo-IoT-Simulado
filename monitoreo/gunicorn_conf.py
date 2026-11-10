import os
import sys

# Este archivo se carga antes que la app: garantiza que `database` se pueda importar.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

bind = '0.0.0.0:5002'
workers = 2
timeout = 30
accesslog = '-'


def on_starting(server):
    """Prepara la base de datos una sola vez, antes de crear los workers.

    Si no se logra, el proceso termina con error y Docker lo reinicia (restart policy).
    """
    from database import inicializar

    if not inicializar():
        server.log.error('[monitoreo] no se pudo preparar la base de datos')
        sys.exit(1)
