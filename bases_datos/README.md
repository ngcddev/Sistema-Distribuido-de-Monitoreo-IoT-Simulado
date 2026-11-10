# Bases de datos

Cada servicio con persistencia tiene su propia base MySQL 8.4 (un contenedor y un
volumen por servicio). MySQL crea la base y un usuario (`DB_USER`) con permisos solo sobre
ella; los servicios crean sus **tablas** al arrancar (`inicializar()` en cada
`database.py`), reintentando mientras MySQL queda disponible.

Los scripts de esta carpeta son **de referencia** y una prueba (`test_esquema_*`) comprueba
que no se desincronicen de `database.py`. Los campos `timestamp` son `DATETIME(3)` en UTC;
la API los entrega en ISO 8601 (`2026-01-02T03:04:05+00:00`). Si tus volúmenes vienen de una
versión anterior (`timestamp` como texto), hay que recrearlos (ver README, "Cambiar credenciales").

| Archivo | Servicio | Base de datos | Tablas |
|---|---|---|---|
| `mediciones.sql` | Mediciones | `mediciones` | `mediciones` |
| `sensores.sql` | Sensores | `sensores` | `sensores` |
| `monitoreo.sql` | Monitoreo | `monitoreo` | `umbrales`, `alertas` |
