bind = '0.0.0.0:8000'
workers = 2
# Mayor que GATEWAY_TIMEOUT: el worker no debe morir antes de poder responder el 504.
timeout = 30
accesslog = '-'
