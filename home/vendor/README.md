# Bibliotecas incluidas (vendor)

Se sirven desde aquí en lugar de un CDN: el Home funciona sin internet y la política de seguridad
(`nginx.conf`) no necesita permitir orígenes externos. Dependabot **no** actualiza estos archivos;
hay que hacerlo a mano.

| Archivo | Biblioteca | Versión | Licencia | SHA-256 |
|---|---|---|---|---|
| `chart.umd.min.js` | [Chart.js](https://www.chartjs.org/) | 4.4.1 | MIT | `d2af8974e95271638772e9e9524db5b9a6f58d6ec2d5d781400447b4a31c681e` |

## Cómo actualizar Chart.js

1. Elegir la versión en <https://github.com/chartjs/Chart.js/releases>.
2. Descargarla y comprobar que se parece al archivo actual:

   ```bash
   curl -fsSL -o home/vendor/chart.umd.min.js \
     https://cdn.jsdelivr.net/npm/chart.js@<VERSION>/dist/chart.umd.min.js
   sha256sum home/vendor/chart.umd.min.js
   ```

3. Actualizar la versión y el SHA-256 de la tabla de arriba.
4. Ejecutar las pruebas del Home (`cd home/e2e && npm test`): comprueban que el gráfico se dibuja, se
   refresca y no rompe la política de seguridad.
