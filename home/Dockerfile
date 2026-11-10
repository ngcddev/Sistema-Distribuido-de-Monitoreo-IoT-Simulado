FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY proxy_params.conf /etc/nginx/proxy_params.conf
COPY index.html style.css script.js favicon.svg /usr/share/nginx/html/
COPY vendor/ /usr/share/nginx/html/vendor/
EXPOSE 8080
