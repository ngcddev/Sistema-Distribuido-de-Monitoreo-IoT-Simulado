#!/usr/bin/env bash
# Pruebas integrales del Tercer avance, ejecutadas contra el stack real a través del API Gateway.
# Uso (con el stack arriba):  bash docs/pruebas/pruebas-integrales.sh [crud|errores|timeout|circuito|caida|persistencia|todo]
# Requiere curl y docker compose. No borra volúmenes.
set -u
cd "$(dirname "$0")/../.."
GW=${GATEWAY_URL:-http://localhost:8000}
CB_TIMEOUT=${CB_TIMEOUT:-10}
FALLOS=0
TMP=$(mktemp)

# req METODO RUTA [JSON] -> imprime la solicitud, el código HTTP y la respuesta; deja el código en $CODIGO
req() {
    local metodo=$1 ruta=$2 cuerpo=${3:-}
    local args=(-s -m 20 -o "$TMP" -w '%{http_code}' -X "$metodo")
    [ -n "$cuerpo" ] && args+=(-H 'Content-Type: application/json' -d "$cuerpo")
    CODIGO=$(curl "${args[@]}" "$GW$ruta")
    CUERPO=$(cat "$TMP")
    printf '  %-7s %-42s -> %s %s\n' "$metodo" "$ruta" "$CODIGO" "${CUERPO:0:150}"
}
esperar() { # esperar CODIGO_ESPERADO
    if [ "$CODIGO" = "$1" ]; then echo "    OK (HTTP $1)"; else echo "    FALLO: se esperaba $1"; FALLOS=$((FALLOS+1)); fi
}
id_de() { echo "$CUERPO" | tr -d '\n ' | sed -n 's/.*"id":\([0-9]*\).*/\1/p' | head -1; }
titulo() { printf '\n=== %s ===\n' "$1"; }
circuito_json() { curl -s "$GW/monitoreo/circuitos" | tr -d '\n ' | sed 's/.*"mediciones":{\([^}]*\)}.*/\1/'; }
esperar_sano() { # esperar_sano SERVICIO
    for _ in $(seq 1 40); do docker compose ps "$1" 2>/dev/null | grep -q healthy && return 0; sleep 2; done
}

crud_recurso() { # crud_recurso NOMBRE RUTA JSON_CREAR JSON_ACTUALIZAR TEXTO_QUE_DEBE_QUEDAR
    local nombre=$1 ruta=$2
    titulo "CRUD $nombre"
    req POST "$ruta" "$3";        esperar 201
    local id; id=$(id_de)
    req GET  "$ruta/$id";         esperar 200
    req PUT  "$ruta/$id" "$4";    esperar 200
    req GET  "$ruta/$id";         esperar 200
    if echo "$CUERPO" | grep -q "$5"; then echo "    OK: la modificación quedó almacenada ($5)"; else echo "    FALLO: no se guardó $5"; FALLOS=$((FALLOS+1)); fi
    req DELETE "$ruta/$id";       esperar 200
    req GET  "$ruta/$id";         esperar 404
    req GET  "$ruta/999999";      esperar 404
    req DELETE "$ruta/999999";    esperar 404
}

prueba_crud() {
    crud_recurso "Sensores" /sensores \
        '{"nombre":"Sensor prueba","tipo":"humedad","ubicacion":"vivero","activo":true}' \
        '{"nombre":"Sensor prueba editado","tipo":"temperatura","ubicacion":"vivero","activo":false}' 'prueba editado'
    crud_recurso "Mediciones" /mediciones \
        '{"sensor_id":1,"valor":21.5,"unidad":"C"}' \
        '{"sensor_id":1,"valor":33.3,"unidad":"C"}' '33.3'
    crud_recurso "Umbrales" /monitoreo/umbrales \
        '{"tipo":"presion","minimo":900,"maximo":1100,"unidad":"hPa"}' \
        '{"tipo":"presion","minimo":950,"maximo":1050,"unidad":"hPa"}' '1050'
    titulo "Alertas (se generan al evaluar; solo lectura y borrado)"
    req GET "/monitoreo/alertas?limit=1";   esperar 200
    req GET /monitoreo/alertas/999999;      esperar 404
    req DELETE /monitoreo/alertas/999999;   esperar 404
    titulo "Validaciones y rutas desconocidas"
    req POST /sensores '{"nombre":"x","tipo":"invalido"}';  esperar 400
    req GET /ruta-inexistente;              esperar 404
}

prueba_errores() {
    titulo "Comunicación entre servicios (Monitoreo -> Mediciones y Sensores)"
    req GET /monitoreo/resumen-general;     esperar 200
    req GET /monitoreo/evaluar/1;           esperar 200
    req GET /monitoreo/1;                   esperar 200
    req GET /monitoreo/circuitos;           esperar 200
}

demora() { req PUT /mediciones/simulacion/demora "{\"segundos\":$1}"; esperar 200; }

prueba_timeout() {
    titulo "Timeout (Monitoreo -> Mediciones: ${MEDICIONES_TIMEOUT:-3} s)"
    echo " 1) Normal"
    req GET /monitoreo/resumen-general;     esperar 200
    echo " 2) Respuesta lenta: Mediciones tarda 6 s (> timeout)"
    demora 6
    req GET /monitoreo/resumen-general;     esperar 504
    echo " 3) Se restablece el comportamiento normal"
    demora 0
    sleep "$((CB_TIMEOUT + 1))"   # deja que el circuito, si se abrió, pase a HALF_OPEN
    req GET /monitoreo/resumen-general;     esperar 200
    echo "    $(circuito_json)"
}

prueba_circuito() {
    titulo "Circuit Breaker (Monitoreo -> Mediciones: umbral ${CB_MAX_FAILS:-3} fallas, recuperación ${CB_TIMEOUT} s)"
    echo " 1) Estado inicial"
    echo "    $(circuito_json)"
    echo " 2) Fallas técnicas controladas: se detiene Mediciones"
    docker compose stop mediciones >/dev/null 2>&1
    for _ in 1 2 3; do req GET /monitoreo/resumen-general; echo "    contador -> $(circuito_json)"; done
    echo " 3) Circuito abierto: la solicitud se rechaza sin llamar a Mediciones"
    req GET /monitoreo/resumen-general;     esperar 503
    echo "    $(circuito_json)"
    echo " 4) Se restablece Mediciones (el circuito sigue OPEN hasta cumplirse el tiempo de recuperación)"
    docker compose start mediciones >/dev/null 2>&1
    esperar_sano mediciones
    req GET /monitoreo/resumen-general;     esperar 503
    echo " 5) Pasados ${CB_TIMEOUT} s: HALF_OPEN deja pasar una solicitud de prueba"
    sleep "$((CB_TIMEOUT + 1))"
    echo "    antes de la prueba: $(circuito_json)"
    if circuito_json | grep -q '"estado":"HALF_OPEN"'; then echo "    OK (HALF_OPEN)"; else echo "    FALLO: se esperaba HALF_OPEN"; FALLOS=$((FALLOS+1)); fi
    req GET /monitoreo/resumen-general;     esperar 200
    echo " 6) Recuperación: vuelve a CLOSED"
    echo "    $(circuito_json)"
    if circuito_json | grep -q '"estado":"CLOSED"'; then echo "    OK (CLOSED)"; else echo "    FALLO: no volvió a CLOSED"; FALLOS=$((FALLOS+1)); fi
}

prueba_caida() {
    titulo "Simulación de fallos: docker compose stop sensores"
    req GET /sensores;                      esperar 200
    docker compose stop sensores >/dev/null 2>&1
    echo " Con Sensores detenido:"
    req GET /sensores;                      esperar 503
    req GET "/mediciones?limit=1";          esperar 200
    req GET /monitoreo/evaluar/1;           esperar 200   # respaldo: el tipo se deduce de la unidad
    docker compose start sensores >/dev/null 2>&1
    esperar_sano sensores
    echo " Recuperado:"
    req GET /sensores;                      esperar 200
}

prueba_persistencia() {
    titulo "Persistencia: se recrean los contenedores de aplicación SIN borrar volúmenes"
    req POST /sensores '{"nombre":"Sensor persistente","tipo":"temperatura","ubicacion":"lab"}'; esperar 201
    local id; id=$(id_de)
    req POST /monitoreo/umbrales '{"tipo":"luz","minimo":10,"maximo":900,"unidad":"lx"}'; esperar 201
    local uid; uid=$(id_de)
    docker compose rm -sf sensores mediciones monitoreo gateway home simulador >/dev/null 2>&1
    docker compose up -d >/dev/null 2>&1
    esperar_sano gateway
    echo " Tras recrear los contenedores:"
    req GET "/sensores/$id";                esperar 200
    req GET "/monitoreo/umbrales/$uid";     esperar 200
    req GET "/mediciones?limit=1";          esperar 200
    req DELETE "/sensores/$id" >/dev/null; req DELETE "/monitoreo/umbrales/$uid" >/dev/null
}

case "${1:-todo}" in
    crud) prueba_crud ;;
    errores) prueba_errores ;;
    timeout) prueba_timeout ;;
    circuito) prueba_circuito ;;
    caida) prueba_caida ;;
    persistencia) prueba_persistencia ;;
    todo) prueba_errores; prueba_crud; prueba_timeout; prueba_circuito; prueba_caida; prueba_persistencia ;;
    *) echo "uso: $0 [crud|errores|timeout|circuito|caida|persistencia|todo]"; exit 2 ;;
esac
rm -f "$TMP"
echo
if [ "$FALLOS" -eq 0 ]; then echo "RESULTADO: todas las comprobaciones pasaron"; else echo "RESULTADO: $FALLOS comprobaciones fallaron"; exit 1; fi
