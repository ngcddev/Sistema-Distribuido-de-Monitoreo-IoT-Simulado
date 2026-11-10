#!/bin/sh
# Se ejecuta al arrancar el contenedor (antes que Nginx), como parte del entrypoint de la imagen.
# Genera /tmp/credenciales.conf con las credenciales de administración que Nginx exige para
# escribir (POST/PUT/PATCH/DELETE). Se guardan como la cabecera "Authorization: Basic ..." esperada.
set -eu

: "${HOME_ADMIN_USER:?falta HOME_ADMIN_USER}"
: "${HOME_ADMIN_PASSWORD:?falta HOME_ADMIN_PASSWORD}"

# base64 sin saltos de línea (busybox parte la salida cada 76 caracteres)
esperado=$(printf '%s:%s' "$HOME_ADMIN_USER" "$HOME_ADMIN_PASSWORD" | base64 | tr -d '\n')

cat > /tmp/credenciales.conf <<EOF
# Generado por 15-credenciales.sh: no editar.
map \$http_authorization \$credenciales_ok {
    default 0;
    "Basic ${esperado}" 1;
}
EOF

echo "15-credenciales.sh: credenciales de administración configuradas para el usuario '$HOME_ADMIN_USER'"
