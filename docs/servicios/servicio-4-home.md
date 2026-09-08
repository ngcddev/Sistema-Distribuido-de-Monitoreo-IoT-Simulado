# Servicio 4: Home

## Resumen

Servicio frontend estático que presenta el estado del sistema en una interfaz web simple, accesible desde un navegador y servida por Nginx dentro de un contenedor Docker.

Su función principal es mostrar al usuario una vista resumida del proyecto, sin incluir lógica de negocio ni procesamiento de sensores. Se concentra en la capa de presentación y permite verificar rápidamente que el sistema está ejecutándose y que la interfaz puede visualizarse correctamente.

## Responsabilidades

- Servir la interfaz web principal del proyecto.
- Exponer una vista de dashboard simple para el usuario final.
- Mostrar información visual y estructural del sistema.
- Actuar como punto de entrada del usuario desde el navegador.
- Ejecutarse como contenido estático en un servidor web ligero.

## Información técnica

| Elemento | Valor |
|---|---| 
| Código | `home/` |
| Tipo | Frontend estático |
| Motor | Nginx |
| Puerto expuesto | `80` |
| Contenedor | `home` |
| Formato de contenido | HTML, CSS y JavaScript |

## Estructura del servicio

La carpeta `home/` contiene los archivos que componen la interfaz:

- `index.html`: estructura principal del dashboard.
- `style.css`: estilos visuales de la vista.
- `script.js`: comportamiento del cliente y carga de datos.
- `Dockerfile`: configuración del contenedor Nginx.

## Ejecución local

Para levantar el servicio por separado:

```bash
docker build -t home ./home
docker run -p 80:80 home
```

Luego se puede abrir en el navegador en:

```text
http://localhost
```

## Configuración del contenedor

El `Dockerfile` del servicio usa una imagen base de Nginx y copia el contenido estático a la carpeta pública del servidor:

```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Este enfoque permite servir el frontend sin necesidad de un backend adicional en la capa de presentación.

## Flujo de operación

1. El usuario accede al puerto `80` del contenedor.
2. Nginx sirve los archivos `index.html`, `style.css` y `script.js`.
3. La interfaz renderiza la vista principal del proyecto.
4. El navegador presenta la información al usuario final.

## Integración con el sistema

El servicio Home no consume directamente los endpoints de los microservicios de la lógica del sistema, sino que funciona como una capa visual de acceso para la aplicación.

Su integración real se realizará cuando la interfaz necesite conectarse con servicios de Mediciones o Monitoreo para mostrar datos en tiempo real o históricos.

## Estado actual

El servicio Home forma parte de la estructura del proyecto como interfaz estática y sirve como base para una futura vista de monitoreo con datos reales. Actualmente se encuentra preparado como contenedor independiente y listo para ser incorporado más adelante a la composición global del sistema con Docker Compose.

## Observaciones de diseño

- Es un frontend minimalista y ligero.
- Está desacoplado de la lógica de negocio.
- Facilita pruebas rápidas de despliegue y visualización.
- Sirve como base para una futura UI de monitoreo interactiva.

## Relación con otros servicios

| Servicio | Relación |
|---|---|
| Mediciones | Consumirá datos para mostrar lecturas y estados |
| Monitoreo | Mostrará alertas, análisis y resúmenes |
| Simulador | Generará la información que eventualmente la vista mostrará |

## Conclusión

El servicio Home cumple una función importante dentro del sistema: ofrecer una entrada visual clara al proyecto, mantener una interfaz de presentación simple y dejar preparada la base para una futura experiencia de monitoreo completa.
