document.addEventListener('DOMContentLoaded', () => {
    const vistaGeneral = document.getElementById('vista-monitoreo');
    const vistaAdmin = document.getElementById('vista-mediciones');
    const vistaSensores = document.getElementById('vista-sensores');
    const menuGeneral = document.getElementById('menu-general');
    const menuAdmin = document.getElementById('menu-admin');
    const menuSensores = document.getElementById('menu-sensores');
    const titulo = document.getElementById('titulo-vista');
    const statusText = document.getElementById('status');
    const resultado = document.getElementById('resultado');
    const lecturas = document.getElementById('lecturas');
    const sensorInput = document.getElementById('sensor-id');
    const valorInput = document.getElementById('valor');
    const filaInput = document.getElementById('fila-id');
    const unidadInput = document.getElementById('unidad');

    // Cada entrada del menú muestra una sola vista y oculta las demás.
    const vistas = [
        { menu: menuGeneral, vista: vistaGeneral, titulo: 'Vista general' },
        { menu: menuSensores, vista: vistaSensores, titulo: 'Sensores' },
        { menu: menuAdmin, vista: vistaAdmin, titulo: 'Administración' }
    ];

    function mostrarVista(elegida) {
        vistas.forEach(function (v) {
            const activa = v === elegida;
            v.vista.classList.toggle('vista-oculta', !activa);
            v.menu.classList.toggle('active', activa);
        });
        titulo.textContent = elegida.titulo;
    }

    function mostrarGeneral() {
        mostrarVista(vistas[0]);
    }

    function mostrarSensores() {
        mostrarVista(vistas[1]);
        listarSensores();
    }

    function mostrarAdmin() {
        mostrarVista(vistas[2]);
        consultarTotal();
    }

    function marcarEstado(texto, color) {
        statusText.style.color = color;
        statusText.textContent = texto;
    }

    // Los datos vienen de la API y se insertan con innerHTML: se escapan para evitar XSS.
    function escapar(valor) {
        return String(valor).replace(/[&<>"']/g, function (c) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
        });
    }

    function textoFila(item) {
        let texto = 'id ' + escapar(item.id) + ' | sensor ' + escapar(item.sensor_id) + ': ' + escapar(item.valor) + ' ' + escapar(item.unidad || '');
        if (item.timestamp) {
            texto += ' (' + escapar(item.timestamp) + ')';
        }
        return texto;
    }

    function textoResultado(method, data) {
        if (method === 'DELETE') {
            return 'Eliminada la fila ' + data.id + '. ' + (data.mensaje || '');
        }
        const lineas = [];
        if (data.mensaje) {
            lineas.push(data.mensaje);
        }
        if (data.id !== undefined) {
            lineas.push('id ' + data.id);
        }
        if (data.sensor_id !== undefined) {
            lineas.push('sensor ' + data.sensor_id);
        }
        if (data.valor !== undefined) {
            lineas.push('valor ' + data.valor);
        }
        if (data.unidad) {
            lineas.push('unidad ' + data.unidad);
        }
        if (data.timestamp) {
            lineas.push(data.timestamp);
        }
        return method + ' devolvió: ' + lineas.join(' | ');
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

    async function consultarTotal() {
        marcarEstado('Consultando todas las mediciones...', '#d97706');
        try {
            const respuesta = await fetch('/mediciones');
            if (!respuesta.ok) {
                throw new Error('Mediciones respondió ' + respuesta.status);
            }
            const todas = await respuesta.json();
            const recientes = todas.slice(-8).reverse();
            lecturas.innerHTML = 'Total: ' + todas.length + ' lecturas. Últimas ' + recientes.length + ':<br>' +
                recientes.map(textoFila).join('<br>');
            resultado.textContent = '';
            marcarEstado('GET total ' + respuesta.status, '#10b981');
        } catch (error) {
            marcarEstado(error.message, '#b91c1c');
        }
    }

    async function consultarPorId() {
        const filaId = filaInput.value;
        if (!filaId) {
            resultado.textContent = 'Escribe el id de la fila.';
            marcarEstado(resultado.textContent, '#b91c1c');
            return;
        }
        marcarEstado('Consultando la fila ' + filaId + '...', '#d97706');
        try {
            const respuesta = await fetch('/mediciones/' + encodeURIComponent(filaId));
            const data = await respuesta.json().catch(function () { return {}; });
            if (!respuesta.ok) {
                resultado.textContent = data.error || ('GET respondió ' + respuesta.status);
                lecturas.innerHTML = '';
                marcarEstado(resultado.textContent, '#b91c1c');
                return;
            }
            llenarCampos(data);
            resultado.textContent = textoResultado('GET', data);
            lecturas.innerHTML = '<strong>' + textoFila(data) + ' ← esta fila</strong>';
            marcarEstado('GET por id ' + respuesta.status, '#10b981');
        } catch (error) {
            marcarEstado(error.message, '#b91c1c');
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
            resultado.textContent = 'Escribe el id de la fila.';
            marcarEstado(resultado.textContent, '#b91c1c');
            return;
        }
        if ((method === 'POST' || method === 'PUT' || method === 'PATCH') && valorInput.value === '') {
            resultado.textContent = 'Escribe el valor.';
            marcarEstado(resultado.textContent, '#b91c1c');
            return;
        }
        if ((method === 'POST' || method === 'PUT') && sensorId === '') {
            resultado.textContent = 'Escribe el sensor.';
            marcarEstado(resultado.textContent, '#b91c1c');
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

        const url = method === 'POST' ? '/mediciones' : '/mediciones/' + filaId;
        marcarEstado(method + ' hacia Mediciones...', '#d97706');
        const respuesta = await fetch(url, opciones);
        const data = await respuesta.json().catch(function () { return {}; });
        if (!respuesta.ok) {
            resultado.textContent = data.error || (method + ' respondió ' + respuesta.status);
            marcarEstado(resultado.textContent, '#b91c1c');
            return;
        }
        llenarCampos(data);
        resultado.textContent = textoResultado(method, data);
        if (method === 'DELETE') {
            lecturas.textContent = 'La fila ' + data.id + ' ya no está.';
        } else if (data.id !== undefined) {
            lecturas.innerHTML = '<strong>' + textoFila(data) + ' ← esta fila</strong>';
        }
        marcarEstado(method + ' ' + respuesta.status, '#10b981');
    }

    menuGeneral.addEventListener('click', function (event) {
        event.preventDefault();
        mostrarGeneral();
    });
    menuAdmin.addEventListener('click', function (event) {
        event.preventDefault();
        mostrarAdmin();
    });
    menuSensores.addEventListener('click', function (event) {
        event.preventDefault();
        mostrarSensores();
    });
    document.getElementById('btn-get-total').addEventListener('click', consultarTotal);
    document.getElementById('btn-get-id').addEventListener('click', consultarPorId);
    document.getElementById('btn-post').addEventListener('click', function () { enviarMedicion('POST'); });
    document.getElementById('btn-put').addEventListener('click', function () { enviarMedicion('PUT'); });
    document.getElementById('btn-patch').addEventListener('click', function () { enviarMedicion('PATCH'); });
    document.getElementById('btn-delete').addEventListener('click', function () { enviarMedicion('DELETE'); });

    // =========================================
    // CATÁLOGO DE SENSORES (GET/POST/PUT/DELETE /sensores a través del Gateway)
    // Se construye el DOM con createElement/textContent: sin innerHTML ni estilos en línea.
    // =========================================
    const sensoresEstado = document.getElementById('sensores-estado');
    const sensoresCuerpo = document.getElementById('sensores-cuerpo');
    const filtroTipo = document.getElementById('filtro-tipo');
    const filtroActivo = document.getElementById('filtro-activo');
    const formSensor = document.getElementById('form-sensor');
    const sensorNombre = document.getElementById('sensor-nombre');
    const sensorTipo = document.getElementById('sensor-tipo');
    const sensorUbicacion = document.getElementById('sensor-ubicacion');
    const sensorActivo = document.getElementById('sensor-activo');

    function estadoSensores(texto, clase) {
        sensoresEstado.textContent = texto;
        sensoresEstado.classList.remove('estado-ok', 'estado-espera', 'estado-error');
        sensoresEstado.classList.add(clase);
    }

    async function pedirJson(url, opciones) {
        const respuesta = await fetch(url, opciones);
        const data = await respuesta.json().catch(function () { return {}; });
        if (!respuesta.ok) {
            throw new Error(data.error || ('Sensores respondió ' + respuesta.status));
        }
        return { codigo: respuesta.status, data: data };
    }

    function celda(texto, clase) {
        const td = document.createElement('td');
        td.textContent = texto;
        if (clase) {
            td.className = clase;
        }
        return td;
    }

    function boton(texto, clase, alPulsar) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = clase;
        b.textContent = texto;
        b.addEventListener('click', alPulsar);
        return b;
    }

    function filaSensor(sensor) {
        const tr = document.createElement('tr');
        tr.dataset.id = sensor.id;
        tr.appendChild(celda(sensor.id));
        tr.appendChild(celda(sensor.nombre));
        tr.appendChild(celda(sensor.tipo));
        tr.appendChild(celda(sensor.ubicacion || '—'));
        tr.appendChild(celda(sensor.activo ? 'Activo' : 'Inactivo', sensor.activo ? 'estado-activo' : 'estado-inactivo'));

        const acciones = document.createElement('td');
        const contenedor = document.createElement('div');
        contenedor.className = 'acciones';
        contenedor.appendChild(boton(sensor.activo ? 'Desactivar' : 'Activar', 'btn-secondary', function () {
            cambiarActivo(sensor);
        }));
        contenedor.appendChild(boton('Eliminar', 'btn-danger', function () {
            eliminarSensor(sensor);
        }));
        acciones.appendChild(contenedor);
        tr.appendChild(acciones);
        return tr;
    }

    function pintarSensores(sensores) {
        const filas = sensores.length ? sensores.map(filaSensor) : (function () {
            const tr = document.createElement('tr');
            const td = celda('No hay sensores con esos filtros.', 'vacio');
            td.colSpan = 6;
            tr.appendChild(td);
            return [tr];
        })();
        sensoresCuerpo.replaceChildren.apply(sensoresCuerpo, filas);
    }

    async function listarSensores() {
        const parametros = new URLSearchParams();
        if (filtroTipo.value) {
            parametros.set('tipo', filtroTipo.value);
        }
        if (filtroActivo.value) {
            parametros.set('activo', filtroActivo.value);
        }
        const consulta = parametros.toString();
        const url = '/sensores' + (consulta ? '?' + consulta : '');
        estadoSensores('Consultando ' + url + '...', 'estado-espera');
        try {
            const r = await pedirJson(url);
            pintarSensores(r.data);
            estadoSensores('GET ' + url + ' ' + r.codigo + ' (' + r.data.length + ' sensores)', 'estado-ok');
        } catch (error) {
            sensoresCuerpo.replaceChildren();
            estadoSensores(error.message, 'estado-error');
        }
    }

    async function crearSensor(event) {
        event.preventDefault();
        const nombre = sensorNombre.value.trim();
        if (!nombre) {
            estadoSensores('Escribe el nombre del sensor.', 'estado-error');
            return;
        }
        estadoSensores('POST /sensores...', 'estado-espera');
        try {
            const r = await pedirJson('/sensores', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nombre: nombre,
                    tipo: sensorTipo.value,
                    ubicacion: sensorUbicacion.value.trim() || null,
                    activo: sensorActivo.checked
                })
            });
            formSensor.reset();
            sensorActivo.checked = true;
            await listarSensores();
            estadoSensores('POST /sensores ' + r.codigo + ': creado el sensor ' + r.data.id, 'estado-ok');
        } catch (error) {
            estadoSensores(error.message, 'estado-error');
        }
    }

    async function cambiarActivo(sensor) {
        estadoSensores('PUT /sensores/' + sensor.id + '...', 'estado-espera');
        try {
            const r = await pedirJson('/sensores/' + encodeURIComponent(sensor.id), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nombre: sensor.nombre,
                    tipo: sensor.tipo,
                    ubicacion: sensor.ubicacion,
                    activo: !sensor.activo
                })
            });
            await listarSensores();
            estadoSensores('PUT /sensores/' + sensor.id + ' ' + r.codigo + ': ' + (r.data.activo ? 'activado' : 'desactivado'), 'estado-ok');
        } catch (error) {
            estadoSensores(error.message, 'estado-error');
        }
    }

    async function eliminarSensor(sensor) {
        if (!window.confirm('¿Eliminar el sensor ' + sensor.id + ' (' + sensor.nombre + ')?')) {
            return;
        }
        estadoSensores('DELETE /sensores/' + sensor.id + '...', 'estado-espera');
        try {
            const r = await pedirJson('/sensores/' + encodeURIComponent(sensor.id), { method: 'DELETE' });
            await listarSensores();
            estadoSensores('DELETE /sensores/' + sensor.id + ' ' + r.codigo + ': ' + (r.data.mensaje || 'eliminado'), 'estado-ok');
        } catch (error) {
            estadoSensores(error.message, 'estado-error');
        }
    }

    document.getElementById('btn-sensores-listar').addEventListener('click', listarSensores);
    filtroTipo.addEventListener('change', listarSensores);
    filtroActivo.addEventListener('change', listarSensores);
    formSensor.addEventListener('submit', crearSensor);

    // =========================================
    // INTEGRACIÓN CON MICROSERVICIO DE MONITOREO Y GRÁFICO
    // =========================================
    const panelMonitoreo = document.getElementById('panel-monitoreo');
    const inputSensorMonitoreo = document.getElementById('monitoreo-sensor-id');
    let miGrafico = null;

    async function actualizarGraficoSensor() {
        const sensorId = inputSensorMonitoreo ? inputSensorMonitoreo.value : 1;
        const canvas = document.getElementById('graficoMonitoreo');
        if (!canvas) return;

        try {
            if (typeof Chart === 'undefined') return; // Chart.js no cargó (sin conexión al CDN)
            const respuesta = await fetch('/mediciones?sensor_id=' + encodeURIComponent(sensorId) + '&limit=10');
            if (!respuesta.ok) return;
            const lecturasSensor = await respuesta.json();

            const labels = lecturasSensor.map((l, i) => {
                const fecha = l.timestamp ? new Date(l.timestamp) : null;
                return fecha && !isNaN(fecha) ? fecha.toLocaleTimeString() : `L`;
            });
            const valores = lecturasSensor.map(l => Number(l.valor));

            const ctx = canvas.getContext('2d');

            if (miGrafico) {
                miGrafico.destroy();
            }

            miGrafico = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: `Histórico Sensor ${sensorId}`,
                        data: valores,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
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
            console.log("Error al cargar gráfico:", e);
        }
    }

    async function consultarResumenGeneral() {
        panelMonitoreo.innerHTML = '<em>Cargando métricas globales de la red...</em>';
        try {
            const respuesta = await fetch('/monitoreo/resumen-general');
            if (!respuesta.ok) throw new Error('Error al conectar con Monitoreo');
            const data = await respuesta.json();

            if (data.mensaje) {
                panelMonitoreo.innerHTML = `<p>${escapar(data.mensaje)}</p>`;
                return;
            }

            panelMonitoreo.innerHTML = `
                <strong style="color: #2563eb;">--- Resumen Global de la Red ---</strong><br>
                <strong>Total lecturas registradas:</strong> ${data.total_lecturas_sistema}<br>
                <strong>Sensores activos:</strong> ${data.total_sensores_activos} (${escapar(data.listado_sensores.join(', '))})<br>
                <strong>Promedio general del sistema:</strong> ${data.promedio_global_sistema}
            `;
        } catch (err) {
            panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">Error: ${err.message}. Asegúrate de que el microservicio Monitoreo esté activo.</span>`;
        }
    }

    async function consultarResumenSensor() {
        const sensorId = inputSensorMonitoreo ? inputSensorMonitoreo.value : 1;
        panelMonitoreo.innerHTML = `<em>Consultando métricas para sensor ${sensorId}...</em>`;
        try {
            const respuesta = await fetch(`/monitoreo/${sensorId}`);
            const data = await respuesta.json();

            if (!respuesta.ok) {
                panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">${escapar(data.error || data.mensaje)}</span>`;
                return;
            }

            panelMonitoreo.innerHTML = `
                <strong style="color: #2563eb;">--- Métricas del Sensor ${escapar(data.sensor_id)} ---</strong><br>
                <strong>Cantidad de lecturas:</strong> ${data.cantidad_lecturas}<br>
                <strong>Promedio histórico:</strong> ${data.promedio}<br>
                <strong>Última lectura:</strong> ${escapar(data.ultima_lectura.valor)} ${escapar(data.ultima_lectura.unidad || '')} (${escapar(data.ultima_lectura.timestamp || 'reciente')})
            `;

            actualizarGraficoSensor();
        } catch (err) {
            panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">Error de conexión con el microservicio Monitoreo.</span>`;
        }
    }

    async function evaluarSensor() {
        const sensorId = inputSensorMonitoreo ? inputSensorMonitoreo.value : 1;
        panelMonitoreo.innerHTML = `<em>Evaluando umbrales del sensor ${sensorId}...</em>`;
        try {
            const respuesta = await fetch(`/monitoreo/evaluar/${sensorId}`);
            const data = await respuesta.json();

            if (!respuesta.ok) {
                panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">${escapar(data.error || data.mensaje)}</span>`;
                return;
            }

            const esAlerta = data.evaluacion === 'ALERTA_CRITICA';
            const colorEstado = esAlerta ? '#b91c1c' : '#10b981';

            panelMonitoreo.innerHTML = `
                <strong style="color: ${colorEstado};">--- Evaluación: ${escapar(data.evaluacion)} ---</strong><br>
                <strong>Sensor:</strong> ${escapar(data.sensor_id)} (${escapar(data.tipo || 'tipo desconocido')})<br>
                <strong>Valor evaluado:</strong> ${escapar(data.valor_evaluado)}<br>
                <strong>Diagnóstico:</strong> ${escapar(data.diagnostico)}
            `;

            actualizarGraficoSensor();
        } catch (err) {
            panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">Error de conexión con el microservicio Monitoreo.</span>`;
        }
    }

    async function verUmbrales() {
        panelMonitoreo.innerHTML = '<em>Consultando umbrales...</em>';
        try {
            const respuesta = await fetch('/monitoreo/umbrales');
            if (!respuesta.ok) throw new Error('Monitoreo respondió ' + respuesta.status);
            const umbrales = await respuesta.json();
            panelMonitoreo.innerHTML = '<strong style="color: #2563eb;">--- Umbrales configurados ---</strong><br>' +
                umbrales.map(function (u) {
                    return escapar(u.tipo) + ': ' + escapar(u.minimo) + ' a ' + escapar(u.maximo) + ' ' + escapar(u.unidad || '');
                }).join('<br>');
        } catch (err) {
            panelMonitoreo.innerHTML = '<span style="color: #b91c1c;">Error: ' + escapar(err.message) + '</span>';
        }
    }

    async function verAlertas() {
        panelMonitoreo.innerHTML = '<em>Consultando alertas...</em>';
        try {
            const respuesta = await fetch('/monitoreo/alertas?limit=10');
            if (!respuesta.ok) throw new Error('Monitoreo respondió ' + respuesta.status);
            const alertas = await respuesta.json();
            if (!alertas.length) {
                panelMonitoreo.innerHTML = '<p>No hay alertas registradas. Usa "Evaluar Umbrales" para generarlas.</p>';
                return;
            }
            panelMonitoreo.innerHTML = '<strong style="color: #b91c1c;">--- Últimas alertas ---</strong><br>' +
                alertas.map(function (a) {
                    return 'sensor ' + escapar(a.sensor_id) + ' | ' + escapar(a.valor) + ' | ' + escapar(a.detalle);
                }).join('<br>');
        } catch (err) {
            panelMonitoreo.innerHTML = '<span style="color: #b91c1c;">Error: ' + escapar(err.message) + '</span>';
        }
    }

    document.getElementById('btn-ver-umbrales')?.addEventListener('click', verUmbrales);
    document.getElementById('btn-ver-alertas')?.addEventListener('click', verAlertas);
    document.getElementById('btn-resumen-general')?.addEventListener('click', consultarResumenGeneral);
    document.getElementById('btn-resumen-sensor')?.addEventListener('click', consultarResumenSensor);
    document.getElementById('btn-evaluar-sensor')?.addEventListener('click', evaluarSensor);
});