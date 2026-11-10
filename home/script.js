document.addEventListener('DOMContentLoaded', () => {
    const IDIOMA = 'es';
    const INTERVALO_GRAFICO_MS = 10000;

    const vistaGeneral = document.getElementById('vista-monitoreo');
    const vistaAdmin = document.getElementById('vista-mediciones');
    const menuGeneral = document.getElementById('menu-general');
    const menuAdmin = document.getElementById('menu-admin');
    const titulo = document.getElementById('titulo-vista');
    const statusText = document.getElementById('status');
    const resultado = document.getElementById('resultado');
    const lecturas = document.getElementById('lecturas');
    const sensorInput = document.getElementById('sensor-id');
    const valorInput = document.getElementById('valor');
    const filaInput = document.getElementById('fila-id');
    const unidadInput = document.getElementById('unidad');
    const panelMonitoreo = document.getElementById('panel-monitoreo');
    const inputSensorMonitoreo = document.getElementById('monitoreo-sensor-id');
    let miGrafico = null;

    // ------------------------------------------------------------------ utilidades de DOM
    // Los datos de la API nunca se concatenan en HTML: se insertan como texto (textContent),
    // así no hay que escapar nada y no hay riesgo de XSS.

    function crear(etiqueta, clase, texto) {
        const elemento = document.createElement(etiqueta);
        if (clase) {
            elemento.className = clase;
        }
        if (texto !== undefined) {
            elemento.textContent = texto;
        }
        return elemento;
    }

    // Convierte una lista de líneas (texto o nodos) en nodos separados por <br>.
    function nodosDeLineas(lineas) {
        const nodos = [];
        lineas.forEach(function (linea, i) {
            if (i > 0) {
                nodos.push(document.createElement('br'));
            }
            nodos.push(typeof linea === 'string' ? document.createTextNode(linea) : linea);
        });
        return nodos;
    }

    // Línea "Etiqueta: valor" con la etiqueta en negrita.
    function lineaEtiquetada(etiqueta, valor) {
        const fragmento = document.createDocumentFragment();
        fragmento.append(crear('strong', '', etiqueta + ':'), ' ' + valor);
        return fragmento;
    }

    function mostrarPanel(nodos) {
        panelMonitoreo.replaceChildren(...nodos);
    }

    function mensajePanel(texto, clase, etiqueta) {
        mostrarPanel([crear(etiqueta || 'span', clase, texto)]);
    }

    function resumenPanel(tituloPanel, claseTitulo, lineas) {
        const encabezado = crear('strong', 'titulo-panel ' + claseTitulo, '--- ' + tituloPanel + ' ---');
        mostrarPanel(nodosDeLineas([encabezado, ...lineas]));
    }

    // tipo: info | aviso | ok | error (clases .estado-* de style.css)
    function marcarEstado(texto, tipo) {
        statusText.className = 'status-msg estado-' + tipo;
        statusText.textContent = texto;
    }

    function rechazar(texto) {
        resultado.textContent = texto;
        marcarEstado(texto, 'error');
    }

    // ------------------------------------------------------------------ vistas
    function mostrarGeneral() {
        vistaGeneral.classList.remove('vista-oculta');
        vistaAdmin.classList.add('vista-oculta');
        menuGeneral.classList.add('active');
        menuGeneral.setAttribute('aria-current', 'page');
        menuAdmin.classList.remove('active');
        menuAdmin.removeAttribute('aria-current');
        titulo.textContent = 'Vista general';
    }

    function mostrarAdmin() {
        vistaGeneral.classList.add('vista-oculta');
        vistaAdmin.classList.remove('vista-oculta');
        menuGeneral.classList.remove('active');
        menuGeneral.removeAttribute('aria-current');
        menuAdmin.classList.add('active');
        menuAdmin.setAttribute('aria-current', 'page');
        titulo.textContent = 'Administración';
        consultarTotal();
    }

    // La vista activa vive en la URL (#administracion); los enlaces del menú son enlaces reales.
    function aplicarVistaDesdeHash() {
        if (window.location.hash === '#administracion') {
            mostrarAdmin();
        } else {
            mostrarGeneral();
        }
    }

    // ------------------------------------------------------------------ administración de mediciones
    function textoFila(item) {
        let texto = 'id ' + item.id + ' | sensor ' + item.sensor_id + ': ' + item.valor + ' ' + (item.unidad || '');
        if (item.timestamp) {
            texto += ' (' + item.timestamp + ')';
        }
        return texto;
    }

    function textoResultado(method, data) {
        if (method === 'DELETE') {
            return 'Eliminada la fila ' + data.id + '. ' + (data.mensaje || '');
        }
        const partes = [];
        if (data.mensaje) {
            partes.push(data.mensaje);
        }
        if (data.id !== undefined) {
            partes.push('id ' + data.id);
        }
        if (data.sensor_id !== undefined) {
            partes.push('sensor ' + data.sensor_id);
        }
        if (data.valor !== undefined) {
            partes.push('valor ' + data.valor);
        }
        if (data.unidad) {
            partes.push('unidad ' + data.unidad);
        }
        if (data.timestamp) {
            partes.push(data.timestamp);
        }
        return method + ' devolvió: ' + partes.join(' | ');
    }

    function llenarCampos(fila) {
        if (!fila) {
            return;
        }
        if (fila.id !== undefined) {
            filaInput.value = fila.id;
        }
        if (fila.sensor_id !== undefined) {
            sensorInput.value = fila.sensor_id;
        }
        if (fila.valor !== undefined) {
            valorInput.value = fila.valor;
        }
        if (fila.unidad) {
            unidadInput.value = fila.unidad;
        }
    }

    function mostrarFilaDestacada(data) {
        lecturas.replaceChildren(crear('strong', '', textoFila(data) + ' ← esta fila'));
    }

    async function consultarTotal() {
        marcarEstado('Consultando todas las mediciones…', 'aviso');
        try {
            const [respuesta, respuestaTotal] = await Promise.all([
                fetch('/mediciones?limit=8'),
                fetch('/mediciones/estadisticas')
            ]);
            if (!respuesta.ok || !respuestaTotal.ok) {
                throw new Error('Mediciones respondió ' + (respuesta.ok ? respuestaTotal.status : respuesta.status));
            }
            const recientes = (await respuesta.json()).reverse();
            const estadisticas = await respuestaTotal.json();
            const encabezado = 'Total: ' + estadisticas.total + ' lecturas. Últimas ' + recientes.length + ':';
            lecturas.replaceChildren(...nodosDeLineas([encabezado, ...recientes.map(textoFila)]));
            resultado.textContent = '';
            marcarEstado('GET total ' + respuesta.status, 'ok');
        } catch (error) {
            marcarEstado(error.message, 'error');
        }
    }

    async function consultarPorId() {
        const filaId = filaInput.value;
        if (!filaId) {
            rechazar('Escribe el id de la fila.');
            return;
        }
        marcarEstado('Consultando la fila ' + filaId + '…', 'aviso');
        try {
            const respuesta = await fetch('/mediciones/' + encodeURIComponent(filaId));
            const data = await respuesta.json().catch(function () { return {}; });
            if (!respuesta.ok) {
                lecturas.replaceChildren();
                rechazar(data.error || ('GET respondió ' + respuesta.status));
                return;
            }
            llenarCampos(data);
            resultado.textContent = textoResultado('GET', data);
            mostrarFilaDestacada(data);
            marcarEstado('GET por id ' + respuesta.status, 'ok');
        } catch (error) {
            marcarEstado(error.message, 'error');
        }
    }

    async function enviarMedicion(method) {
        const sensorId = sensorInput.value;
        const filaId = filaInput.value;
        const opciones = {
            method: method,
            headers: { 'Content-Type': 'application/json' }
        };

        if (method !== 'POST' && !filaId) {
            rechazar('Escribe el id de la fila.');
            return;
        }
        if ((method === 'POST' || method === 'PUT' || method === 'PATCH') && valorInput.value === '') {
            rechazar('Escribe el valor.');
            return;
        }
        if ((method === 'POST' || method === 'PUT') && sensorId === '') {
            rechazar('Escribe el sensor.');
            return;
        }

        if (method === 'POST' || method === 'PUT') {
            opciones.body = JSON.stringify({
                sensor_id: Number(sensorId),
                valor: Number(valorInput.value),
                unidad: unidadInput.value
            });
        } else if (method === 'PATCH') {
            opciones.body = JSON.stringify({ valor: Number(valorInput.value) });
        }

        if (method === 'DELETE' && !window.confirm('¿Eliminar la fila ' + filaId + '? Esta acción no se puede deshacer.')) {
            marcarEstado('Eliminación cancelada.', 'info');
            return;
        }

        const url = method === 'POST' ? '/mediciones' : '/mediciones/' + encodeURIComponent(filaId);
        marcarEstado(method + ' hacia Mediciones…', 'aviso');
        try {
            const respuesta = await fetch(url, opciones);
            const data = await respuesta.json().catch(function () { return {}; });
            if (!respuesta.ok) {
                rechazar(data.error || (method + ' respondió ' + respuesta.status));
                return;
            }
            llenarCampos(data);
            resultado.textContent = textoResultado(method, data);
            if (method === 'DELETE') {
                lecturas.textContent = 'La fila ' + data.id + ' ya no está.';
            } else if (data.id !== undefined) {
                mostrarFilaDestacada(data);
            }
            marcarEstado(method + ' ' + respuesta.status, 'ok');
        } catch (error) {
            rechazar('No se pudo conectar con Mediciones: ' + error.message);
        }
    }

    // ------------------------------------------------------------------ monitoreo y gráfico
    function sensorMonitoreo() {
        return inputSensorMonitoreo ? inputSensorMonitoreo.value : '1';
    }

    function colorAzul() {
        return getComputedStyle(document.documentElement).getPropertyValue('--azul').trim() || '#2563eb';
    }

    async function actualizarGraficoSensor() {
        const sensorId = sensorMonitoreo();
        const canvas = document.getElementById('graficoMonitoreo');
        if (!canvas) return;

        try {
            if (typeof Chart === 'undefined') return; // vendor/chart.umd.min.js no cargó
            const respuesta = await fetch('/mediciones?sensor_id=' + encodeURIComponent(sensorId) + '&limit=10');
            if (!respuesta.ok) return;
            const lecturasSensor = await respuesta.json();

            const etiquetas = lecturasSensor.map(function (l) {
                const fecha = l.timestamp ? new Date(l.timestamp) : null;
                return fecha && !isNaN(fecha) ? fecha.toLocaleTimeString(IDIOMA) : '—';
            });
            const valores = lecturasSensor.map(function (l) { return Number(l.valor); });

            if (miGrafico) {
                miGrafico.destroy();
            }

            const azul = colorAzul();
            miGrafico = new Chart(canvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: etiquetas,
                    datasets: [{
                        label: 'Histórico Sensor ' + sensorId,
                        data: valores,
                        borderColor: azul,
                        // Mismo azul con un 10 % de opacidad (hex de 8 dígitos) para el relleno.
                        backgroundColor: /^#[0-9a-f]{6}$/i.test(azul) ? azul + '1a' : azul,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: true } },
                    scales: { y: { beginAtZero: false } }
                }
            });
        } catch (e) {
            console.error('Error al cargar el gráfico:', e);
        }
    }

    async function consultarResumenGeneral() {
        mensajePanel('Cargando métricas globales de la red…', '', 'em');
        try {
            const respuesta = await fetch('/monitoreo/resumen-general');
            if (!respuesta.ok) throw new Error('Error al conectar con Monitoreo');
            const data = await respuesta.json();

            if (data.mensaje) {
                mensajePanel(data.mensaje, '', 'p');
                return;
            }

            // Un promedio por unidad: promediar °C con % no tiene sentido.
            const promedios = Object.entries(data.promedios_por_unidad || {})
                .map(function ([unidad, promedio]) { return promedio + ' ' + unidad; })
                .join(' | ');

            resumenPanel('Resumen Global de la Red', '', [
                lineaEtiquetada('Total lecturas registradas', data.total_lecturas_sistema),
                lineaEtiquetada('Sensores activos', data.total_sensores_activos + ' (' + data.listado_sensores.join(', ') + ')'),
                lineaEtiquetada('Promedio por unidad', promedios)
            ]);
        } catch (err) {
            mensajePanel('Error: ' + err.message + '. Asegúrate de que el microservicio Monitoreo esté activo.', 'texto-error');
        }
    }

    async function consultarResumenSensor() {
        const sensorId = sensorMonitoreo();
        mensajePanel('Consultando métricas para el sensor ' + sensorId + '…', '', 'em');
        try {
            const respuesta = await fetch('/monitoreo/' + encodeURIComponent(sensorId));
            const data = await respuesta.json();

            if (!respuesta.ok) {
                mensajePanel(data.error || data.mensaje, 'texto-error');
                return;
            }

            const ultima = data.ultima_lectura;
            resumenPanel('Métricas del Sensor ' + data.sensor_id, '', [
                lineaEtiquetada('Cantidad de lecturas', data.cantidad_lecturas),
                lineaEtiquetada('Promedio histórico', data.promedio),
                lineaEtiquetada('Última lectura', ultima.valor + ' ' + (ultima.unidad || '') + ' (' + (ultima.timestamp || 'reciente') + ')')
            ]);

            actualizarGraficoSensor();
        } catch (err) {
            mensajePanel('Error de conexión con el microservicio Monitoreo.', 'texto-error');
        }
    }

    async function evaluarSensor() {
        const sensorId = sensorMonitoreo();
        mensajePanel('Evaluando umbrales del sensor ' + sensorId + '…', '', 'em');
        try {
            const respuesta = await fetch('/monitoreo/evaluar/' + encodeURIComponent(sensorId), { method: 'POST' });
            const data = await respuesta.json();

            if (!respuesta.ok) {
                mensajePanel(data.error || data.mensaje, 'texto-error');
                return;
            }

            const esAlerta = data.evaluacion === 'ALERTA_CRITICA';
            resumenPanel('Evaluación: ' + data.evaluacion, esAlerta ? 'texto-error' : 'texto-ok', [
                lineaEtiquetada('Sensor', data.sensor_id + ' (' + (data.tipo || 'tipo desconocido') + ')'),
                lineaEtiquetada('Valor evaluado', data.valor_evaluado),
                lineaEtiquetada('Diagnóstico', data.diagnostico)
            ]);

            actualizarGraficoSensor();
        } catch (err) {
            mensajePanel('Error de conexión con el microservicio Monitoreo.', 'texto-error');
        }
    }

    async function verUmbrales() {
        mensajePanel('Consultando umbrales…', '', 'em');
        try {
            const respuesta = await fetch('/monitoreo/umbrales');
            if (!respuesta.ok) throw new Error('Monitoreo respondió ' + respuesta.status);
            const umbrales = await respuesta.json();
            resumenPanel('Umbrales configurados', '', umbrales.map(function (u) {
                return u.tipo + ': ' + u.minimo + ' a ' + u.maximo + ' ' + (u.unidad || '');
            }));
        } catch (err) {
            mensajePanel('Error: ' + err.message, 'texto-error');
        }
    }

    async function verAlertas() {
        mensajePanel('Consultando alertas…', '', 'em');
        try {
            const respuesta = await fetch('/monitoreo/alertas?limit=10');
            if (!respuesta.ok) throw new Error('Monitoreo respondió ' + respuesta.status);
            const alertas = await respuesta.json();
            if (!alertas.length) {
                mensajePanel('No hay alertas registradas. Usa «Evaluar Umbrales» para generarlas.', '', 'p');
                return;
            }
            resumenPanel('Últimas alertas', 'texto-error', alertas.map(function (a) {
                return 'sensor ' + a.sensor_id + ' | ' + a.valor + ' | ' + a.detalle;
            }));
        } catch (err) {
            mensajePanel('Error: ' + err.message, 'texto-error');
        }
    }

    // ------------------------------------------------------------------ eventos
    window.addEventListener('hashchange', aplicarVistaDesdeHash);
    document.getElementById('btn-get-total').addEventListener('click', consultarTotal);
    document.getElementById('btn-get-id').addEventListener('click', consultarPorId);
    document.getElementById('btn-post').addEventListener('click', function () { enviarMedicion('POST'); });
    document.getElementById('btn-put').addEventListener('click', function () { enviarMedicion('PUT'); });
    document.getElementById('btn-patch').addEventListener('click', function () { enviarMedicion('PATCH'); });
    document.getElementById('btn-delete').addEventListener('click', function () { enviarMedicion('DELETE'); });
    document.getElementById('btn-ver-umbrales').addEventListener('click', verUmbrales);
    document.getElementById('btn-ver-alertas').addEventListener('click', verAlertas);
    document.getElementById('btn-resumen-general').addEventListener('click', consultarResumenGeneral);
    document.getElementById('btn-resumen-sensor').addEventListener('click', consultarResumenSensor);
    document.getElementById('btn-evaluar-sensor').addEventListener('click', evaluarSensor);

    // El gráfico se refresca solo (cada 10 s) mientras se vea la vista general y la pestaña esté activa.
    setInterval(function () {
        if (miGrafico && !document.hidden && !vistaGeneral.classList.contains('vista-oculta')) {
            actualizarGraficoSensor();
        }
    }, INTERVALO_GRAFICO_MS);

    aplicarVistaDesdeHash();
});
