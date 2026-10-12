-- Referencia: mediciones/database.py crea esto automáticamente al arrancar el servicio.
CREATE DATABASE IF NOT EXISTS `mediciones`;
USE `mediciones`;

CREATE TABLE IF NOT EXISTS mediciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sensor_id VARCHAR(50) NOT NULL,
  valor DOUBLE NOT NULL,
  unidad VARCHAR(10),
  timestamp VARCHAR(40) NOT NULL,
  INDEX idx_sensor (sensor_id)
);
