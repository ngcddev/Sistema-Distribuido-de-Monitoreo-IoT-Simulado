Arquitectura — Sistema Distribuido de Monitoreo IoT (Simulado)
1. Descripción general

El sistema permite monitorear sensores (temperatura, humedad, etc.) cuyos datos son generados por un simulador, ya que en este avance no se cuenta con hardware físico. La arquitectura sigue un patrón de microservicios: cada responsabilidad (catálogo de sensores, almacenamiento de mediciones, cálculo de alertas) vive en un servicio independiente que se comunica por HTTP/REST.