FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY proxy_params.conf /etc/nginx/proxy_params.conf
# El entrypoint de la imagen ejecuta los .sh de esta carpeta al arrancar (necesitan permiso de ejecución).
COPY --chmod=755 docker-entrypoint.d/15-credenciales.sh /docker-entrypoint.d/15-credenciales.sh
COPY index.html style.css script.js favicon.svg /usr/share/nginx/html/
COPY vendor/ /usr/share/nginx/html/vendor/
EXPOSE 8080
