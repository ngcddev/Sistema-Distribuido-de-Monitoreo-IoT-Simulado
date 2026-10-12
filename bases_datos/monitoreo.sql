-- Referencia: monitoreo/database.py crea esto automáticamente al arrancar el servicio.
CREATE DATABASE IF NOT EXISTS `monitoreo`;
USE `monitoreo`;

CREATE TABLE IF NOT EXISTS umbrales (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(30) NOT NULL UNIQUE,
  minimo DOUBLE NOT NULL,
  maximo DOUBLE NOT NULL,
  unidad VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medicion_id INT NOT NULL UNIQUE,
  sensor_id VARCHAR(50) NOT NULL,
  tipo VARCHAR(30),
  valor DOUBLE NOT NULL,
  estado VARCHAR(30) NOT NULL,
  detalle VARCHAR(255),
  timestamp VARCHAR(40),
  INDEX idx_sensor (sensor_id)
);

-- Datos iniciales (solo si la tabla umbrales está vacía)
INSERT INTO umbrales (tipo, minimo, maximo, unidad) VALUES
  ('temperatura', 10.0, 35.0, 'C'),
  ('humedad', 30.0, 80.0, '%');
