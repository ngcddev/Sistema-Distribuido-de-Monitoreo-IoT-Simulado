-- Referencia: sensores/database.py crea esto automáticamente al arrancar el servicio.
CREATE DATABASE IF NOT EXISTS `sensores`;
USE `sensores`;

CREATE TABLE IF NOT EXISTS sensores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  tipo VARCHAR(30) NOT NULL,
  ubicacion VARCHAR(80),
  activo TINYINT(1) NOT NULL DEFAULT 1
);

-- Datos iniciales (solo si la tabla está vacía)
INSERT INTO sensores (id, nombre, tipo, ubicacion) VALUES
  (1, 'Temperatura sala', 'temperatura', 'sala'),
  (2, 'Temperatura cocina', 'temperatura', 'cocina'),
  (3, 'Humedad invernadero', 'humedad', 'invernadero');
