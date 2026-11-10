// Pruebas de navegador del Home. No necesitan Docker: un servidor Node sirve los estáticos de `home/`
// con las MISMAS cabeceras de seguridad que `nginx.conf` (se leen de ese archivo) y simula las APIs.
//
//   cd home/e2e && npm install && npm test
//
// Usa el Chrome/Chromium instalado (variable CHROME_PATH para indicar otro ejecutable).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { after, before, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const HOME = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TIPOS = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.svg': 'image/svg+xml' };

function cabecerasDeNginx() {
    const conf = fs.readFileSync(path.join(HOME, 'nginx.conf'), 'utf8');
    const cabeceras = {};
    for (const m of conf.matchAll(/^\s*add_header\s+(\S+)\s+"(.*)"\s+always;/gm)) {
        cabeceras[m[1]] = m[2];
    }
    return cabeceras;
}

function buscarChrome() {
    const candidatos = [
        process.env.CHROME_PATH,
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ];
    const encontrado = candidatos.find((c) => c && fs.existsSync(c));
    assert.ok(encontrado, 'No se encontró Chrome: define CHROME_PATH');
    return encontrado;
}

// ---------------------------------------------------------------- servidor simulado
const ahora = '2026-01-02T03:04:05+00:00';
const lectura = (id) => ({ id, sensor_id: '1', valor: 20 + id, unidad: 'C', timestamp: ahora });

function crearServidor() {
    const estado = { peticiones: [], cortarPost: false };
    const seguridad = cabecerasDeNginx();

    const servidor = http.createServer((req, res) => {
        const url = new URL(req.url, 'http://localhost');
        estado.peticiones.push({ metodo: req.method, ruta: url.pathname + url.search });
        const json = (codigo, cuerpo) => {
            res.writeHead(codigo, { 'Content-Type': 'application/json', ...seguridad });
            res.end(JSON.stringify(cuerpo));
        };
        const ruta = url.pathname;

        if (req.method === 'GET' && !ruta.startsWith('/mediciones') && !ruta.startsWith('/monitoreo')) {
            const archivo = path.join(HOME, ruta === '/' ? 'index.html' : ruta);
            if (!archivo.startsWith(HOME) || !fs.existsSync(archivo) || fs.statSync(archivo).isDirectory()) {
                res.writeHead(404, seguridad);
                return res.end();
            }
            res.writeHead(200, { 'Content-Type': TIPOS[path.extname(archivo)] || 'application/octet-stream', ...seguridad });
            return res.end(fs.readFileSync(archivo));
        }

        if (req.method === 'GET' && ruta === '/mediciones/estadisticas') {
            const respuesta = {
                total: 42,
                sensores: ['1', '2', '3'],
                por_unidad: [
                    { unidad: '%', total: 10, promedio: 61 },
                    { unidad: 'C', total: 32, promedio: 27.3 },
                ],
            };
            if (url.searchParams.get('sensor_id')) respuesta.promedio = 27.3;
            return json(200, respuesta);
        }
        if (req.method === 'GET' && ruta === '/mediciones') {
            const n = Number(url.searchParams.get('limit') || 100);
            return json(200, Array.from({ length: Math.min(n, 10) }, (_, i) => lectura(i + 1)));
        }
        if (req.method === 'GET' && /^\/mediciones\/\d+$/.test(ruta)) return json(200, lectura(Number(ruta.split('/')[2])));
        if (req.method === 'POST' && ruta === '/mediciones') {
            if (estado.cortarPost) return req.socket.destroy();
            return json(201, lectura(99));
        }
        if (req.method === 'DELETE' && /^\/mediciones\/\d+$/.test(ruta)) {
            return json(200, { mensaje: 'medicion eliminada correctamente', id: Number(ruta.split('/')[2]) });
        }
        if (req.method === 'GET' && ruta === '/monitoreo/resumen-general') {
            return json(200, {
                total_lecturas_sistema: 42,
                total_sensores_activos: 3,
                listado_sensores: ['1', '2', '3'],
                promedios_por_unidad: { '%': 61, C: 27.3 },
            });
        }
        if (req.method === 'GET' && ruta === '/monitoreo/1') {
            return json(200, { sensor_id: '1', cantidad_lecturas: 14, promedio: 27.3, ultima_lectura: lectura(14) });
        }
        if (req.method === 'POST' && ruta === '/monitoreo/evaluar/1') {
            return json(200, {
                sensor_id: '1', tipo: 'temperatura', evaluacion: 'ALERTA_CRITICA', valor_evaluado: 99,
                diagnostico: 'El valor 99 C supera el límite máximo permitido (35).', alerta_registrada: true,
            });
        }
        if (req.method === 'GET' && ruta === '/monitoreo/umbrales') {
            return json(200, [{ id: 1, tipo: 'temperatura', minimo: 10, maximo: 35, unidad: 'C' }]);
        }
        if (req.method === 'GET' && ruta === '/monitoreo/alertas') return json(200, []);
        return json(404, { error: 'ruta no simulada: ' + req.method + ' ' + ruta });
    });
    return { servidor, estado };
}

// ---------------------------------------------------------------- pruebas
describe('Home en el navegador', () => {
    let navegador, base, estado, servidor;

    before(async () => {
        ({ servidor, estado } = crearServidor());
        await new Promise((ok) => servidor.listen(0, '127.0.0.1', ok));
        base = `http://127.0.0.1:${servidor.address().port}`;
        navegador = await puppeteer.launch({
            executablePath: buscarChrome(),
            headless: true,
            args: ['--no-sandbox', '--disable-gpu'],
        });
    });

    after(async () => {
        await navegador?.close();
        servidor?.close();
    });

    // Abre una página y acumula todo lo que sea un error (consola, excepciones, recursos que fallan).
    async function abrir(ruta = '/') {
        const pagina = await navegador.newPage();
        const errores = [];
        pagina.on('console', (m) => { if (m.type() === 'error') errores.push('consola: ' + m.text()); });
        pagina.on('pageerror', (e) => errores.push('excepción: ' + e.message));
        pagina.on('requestfailed', (r) => errores.push('petición fallida: ' + r.url()));
        pagina.on('response', (r) => { if (r.status() >= 400) errores.push(`HTTP ${r.status()}: ${r.url()}`); });
        estado.peticiones.length = 0;
        estado.cortarPost = false;
        await pagina.goto(base + ruta, { waitUntil: 'networkidle0' });
        return { pagina, errores };
    }

    const texto = (pagina, selector) => pagina.$eval(selector, (e) => e.textContent);
    const visible = (pagina, selector) => pagina.$eval(selector, (e) => !e.classList.contains('vista-oculta'));
    const metodos = (ruta) => estado.peticiones.filter((p) => p.ruta.startsWith(ruta)).map((p) => p.metodo);

    it('carga sin errores de consola ni violaciones de CSP, con Chart.js local y cabeceras de seguridad', async () => {
        const { pagina, errores } = await abrir();
        assert.equal(await pagina.evaluate(() => typeof Chart), 'function');
        const respuesta = await pagina.goto(base + '/', { waitUntil: 'networkidle0' });
        const cabeceras = respuesta.headers();
        assert.match(cabeceras['content-security-policy'], /script-src 'self'/);
        assert.equal(cabeceras['x-content-type-options'], 'nosniff');
        assert.equal(cabeceras['x-frame-options'], 'DENY');
        assert.deepEqual(errores, []);

        // La política se aplica de verdad: un <script> en línea inyectado desde el DOM debe quedar bloqueado.
        // (No se usa eval(): las evaluaciones de DevTools/Puppeteer se saltan ese bloqueo.)
        const ejecutado = await pagina.evaluate(() => {
            const script = document.createElement('script');
            script.textContent = 'window.__inline = true';
            document.body.appendChild(script);
            return window.__inline === true;
        });
        assert.equal(ejecutado, false, 'la CSP debería bloquear scripts en línea');
        await pagina.close();
    });

    it('no pide nada a un CDN externo', async () => {
        const { pagina } = await abrir();
        const externas = await pagina.evaluate(() => performance.getEntriesByType('resource')
            .map((r) => r.name).filter((n) => !n.startsWith(location.origin)));
        assert.deepEqual(externas, []);
        await pagina.close();
    });

    it('el resumen general muestra un promedio por unidad, sin mezclar °C con %', async () => {
        const { pagina, errores } = await abrir();
        await pagina.click('#btn-resumen-general');
        await pagina.waitForFunction(() => document.getElementById('panel-monitoreo').textContent.includes('Promedio por unidad'));
        const panel = await texto(pagina, '#panel-monitoreo');
        assert.match(panel, /61 %/);
        assert.match(panel, /27\.3 C/);
        assert.doesNotMatch(panel, /undefined|NaN/);
        assert.deepEqual(errores, []);
        await pagina.close();
    });

    it('evaluar un sensor usa POST', async () => {
        const { pagina, errores } = await abrir();
        await pagina.click('#btn-evaluar-sensor');
        await pagina.waitForFunction(() => document.getElementById('panel-monitoreo').textContent.includes('ALERTA_CRITICA'));
        assert.deepEqual(metodos('/monitoreo/evaluar/1'), ['POST']);
        assert.deepEqual(errores, []);
        await pagina.close();
    });

    it('la vista activa vive en la URL y funciona el botón atrás', async () => {
        const { pagina, errores } = await abrir();
        assert.equal(await visible(pagina, '#vista-monitoreo'), true);

        await pagina.click('#menu-admin');
        await pagina.waitForFunction(() => location.hash === '#administracion'
            && !document.getElementById('vista-mediciones').classList.contains('vista-oculta'));
        assert.equal(await visible(pagina, '#vista-mediciones'), true);
        assert.equal(await visible(pagina, '#vista-monitoreo'), false);
        assert.equal(await texto(pagina, '#titulo-vista'), 'Administración');

        await pagina.click('#menu-general');
        await pagina.waitForFunction(() => location.hash === '#general'
            && !document.getElementById('vista-monitoreo').classList.contains('vista-oculta'));
        assert.equal(await visible(pagina, '#vista-monitoreo'), true);

        await pagina.goBack();
        await pagina.waitForFunction(() => location.hash === '#administracion'
            && !document.getElementById('vista-mediciones').classList.contains('vista-oculta'));
        assert.equal(await visible(pagina, '#vista-mediciones'), true);
        assert.deepEqual(errores, []);
        await pagina.close();
    });

    it('abrir /#administracion muestra directamente la administración y consulta las lecturas', async () => {
        const { pagina, errores } = await abrir('/#administracion');
        assert.equal(await visible(pagina, '#vista-mediciones'), true);
        await pagina.waitForFunction(() => document.getElementById('lecturas').textContent.includes('Total: 42 lecturas'));
        assert.ok(metodos('/mediciones?limit=8').length >= 1);
        assert.deepEqual(errores, []);
        await pagina.close();
    });

    it('dibuja el gráfico y lo refresca solo cada 10 s', async () => {
        const { pagina, errores } = await abrir();
        const lecturasDelGrafico = () => estado.peticiones.filter((p) => p.ruta.includes('sensor_id=1&limit=10')).length;

        await pagina.click('#btn-resumen-sensor');
        await pagina.waitForFunction(() => window.Chart.getChart('graficoMonitoreo') !== undefined);
        const antes = lecturasDelGrafico();
        assert.ok(antes >= 1);

        await new Promise((ok) => setTimeout(ok, 10500));
        assert.ok(lecturasDelGrafico() > antes, 'el gráfico debería haberse refrescado');
        assert.deepEqual(errores, []);
        await pagina.close();
    });

    it('DELETE pide confirmación: cancelar no borra, aceptar sí', async () => {
        const { pagina, errores } = await abrir('/#administracion');
        await pagina.waitForFunction(() => document.getElementById('lecturas').textContent.includes('Total'));
        await pagina.type('#fila-id', '5');

        const mensajes = [];
        pagina.once('dialog', async (d) => { mensajes.push(d.message()); await d.dismiss(); });
        await pagina.click('#btn-delete');
        await new Promise((ok) => setTimeout(ok, 300));
        assert.deepEqual(metodos('/mediciones/5'), []);
        assert.match(mensajes[0], /Eliminar la fila 5/);
        assert.match(await texto(pagina, '#status'), /cancelada/);

        pagina.once('dialog', async (d) => { await d.accept(); });
        await pagina.click('#btn-delete');
        await pagina.waitForFunction(() => document.getElementById('status').textContent.includes('DELETE 200'));
        assert.deepEqual(metodos('/mediciones/5'), ['DELETE']);
        assert.deepEqual(errores.filter((e) => !e.includes('ERR_')), []);
        await pagina.close();
    });

    it('si Mediciones no responde, muestra un error claro en vez de quedarse colgado', async () => {
        const { pagina } = await abrir('/#administracion');
        await pagina.waitForFunction(() => document.getElementById('lecturas').textContent.includes('Total'));
        await pagina.type('#valor', '20');
        estado.cortarPost = true;
        await pagina.click('#btn-post');
        await pagina.waitForFunction(() => document.getElementById('status').textContent.includes('No se pudo conectar'));
        assert.match(await texto(pagina, '#status'), /No se pudo conectar con Mediciones/);
        await pagina.close();
    });

    it('los estados se anuncian a lectores de pantalla (aria-live) y los colores tienen contraste', async () => {
        const { pagina } = await abrir();
        for (const selector of ['#status', '#resultado', '#panel-monitoreo']) {
            const live = await pagina.$eval(selector, (e) => e.getAttribute('aria-live'));
            assert.equal(live, 'polite', selector);
        }
        const fuente = fs.readFileSync(path.join(HOME, 'script.js'), 'utf8');
        assert.doesNotMatch(fuente, /#10b981|#d97706/, 'colores de bajo contraste');
        await pagina.close();
    });
});
