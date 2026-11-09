import sys

bind = '0.0.0.0:5001'
workers = 2
timeout = 30
accesslog = '-'


def on_starting(server):
    """Prepara la base de datos una sola vez, antes de crear los workers.

    Si no se logra, el proceso termina con error y Docker lo reinicia (restart policy).
    """
    from database import inicializar

    if not inicializar():
        server.log.error('[mediciones] no se pudo preparar la base de datos')
        sys.exit(1)
