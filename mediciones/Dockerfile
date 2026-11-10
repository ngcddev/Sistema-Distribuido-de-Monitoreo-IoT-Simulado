FROM python:3.12-slim

# Usuario sin privilegios: si el servicio se compromete, no corre como root.
RUN useradd --system --no-create-home --uid 10001 app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER app

EXPOSE 5001

CMD ["gunicorn", "-c", "gunicorn_conf.py", "app:app"]
