# Bases de datos

Cada servicio con persistencia tiene su propia base MySQL 8.0 (un contenedor y un
volumen por servicio). Los scripts de esta carpeta son **de referencia**: los servicios
crean su base y sus tablas por sí solos al arrancar (`inicializar()` en cada
`database.py`), reintentando mientras MySQL queda disponible. Esto requiere un usuario
con permiso `CREATE`; por defecto se usa `root`.

| Archivo | Servicio | Base de datos | Tablas |
|---|---|---|---|
| `mediciones.sql` | Mediciones | `mediciones` | `mediciones` |
| `sensores.sql` | Sensores | `sensores` | `sensores` |
| `monitoreo.sql` | Monitoreo | `monitoreo` | `umbrales`, `alertas` |
