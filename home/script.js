document.addEventListener('DOMContentLoaded', () => {
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

    function mostrarGeneral() {
        vistaGeneral.classList.remove('vista-oculta');
        vistaAdmin.classList.add('vista-oculta');
        menuGeneral.classList.add('active');
        menuAdmin.classList.remove('active');
        titulo.textContent = 'Vista general';
    }

    function mostrarAdmin() {
        vistaGeneral.classList.add('vista-oculta');
        vistaAdmin.classList.remove('vista-oculta');
        menuGeneral.classList.remove('active');
        menuAdmin.classList.add('active');
        titulo.textContent = 'Administración';
        consultarTotal();
    }

    function marcarEstado(texto, color) {
        statusText.style.color = color;
        statusText.textContent = texto;
    }

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
            const respuesta = await fetch('/mediciones?id=' + filaId);
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
            lecturas.innerHTML = 'La fila ' + data.id + ' ya no está.';
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
    document.getElementById('btn-get-total').addEventListener('click', consultarTotal);
    document.getElementById('btn-get-id').addEventListener('click', consultarPorId);
    document.getElementById('btn-post').addEventListener('click', function () { enviarMedicion('POST'); });
    document.getElementById('btn-put').addEventListener('click', function () { enviarMedicion('PUT'); });
    document.getElementById('btn-patch').addEventListener('click', function () { enviarMedicion('PATCH'); });
    document.getElementById('btn-delete').addEventListener('click', function () { enviarMedicion('DELETE'); });

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
            const respuesta = await fetch('/mediciones');
            if (!respuesta.ok) return;
            const todas = await respuesta.json();
            
            const lecturasSensor = todas.filter(l => String(l.sensor_id) === String(sensorId)).slice(-10);

            const labels = lecturasSensor.map((l, i) => l.timestamp ? l.timestamp.split(' ')[1] || `L${i+1}` : `L${i+1}`);
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
                panelMonitoreo.innerHTML = `<p>${data.mensaje}</p>`;
                return;
            }

            panelMonitoreo.innerHTML = `
                <strong style="color: #2563eb;">--- Resumen Global de la Red ---</strong><br>
                <strong>Total lecturas registradas:</strong> ${data.total_lecturas_sistema}<br>
                <strong>Sensores activos:</strong> ${data.total_sensores_activos} (${data.listado_sensores.join(', ')})<br>
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
                panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">${data.error || data.mensaje}</span>`;
                return;
            }

            panelMonitoreo.innerHTML = `
                <strong style="color: #2563eb;">--- Métricas del Sensor ${data.sensor_id} ---</strong><br>
                <strong>Cantidad de lecturas:</strong> ${data.cantidad_lecturas}<br>
                <strong>Promedio histórico:</strong> ${data.promedio}<br>
                <strong>Última lectura:</strong> ${data.ultima_lectura.valor} ${data.ultima_lectura.unidad || ''} (${data.ultima_lectura.timestamp || 'reciente'})
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
                panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">${data.error || data.mensaje}</span>`;
                return;
            }

            const esAlerta = data.evaluacion === 'ALERTA_CRITICA';
            const colorEstado = esAlerta ? '#b91c1c' : '#10b981';

            panelMonitoreo.innerHTML = `
                <strong style="color: ${colorEstado};">--- Evaluación: ${data.evaluacion} ---</strong><br>
                <strong>Sensor:</strong> ${data.sensor_id}<br>
                <strong>Valor evaluado:</strong> ${data.valor_evaluado}<br>
                <strong>Diagnóstico:</strong> ${data.diagnostico}
            `;

            actualizarGraficoSensor();
        } catch (err) {
            panelMonitoreo.innerHTML = `<span style="color: #b91c1c;">Error de conexión con el microservicio Monitoreo.</span>`;
        }
    }

    document.getElementById('btn-resumen-general')?.addEventListener('click', consultarResumenGeneral);
    document.getElementById('btn-resumen-sensor')?.addEventListener('click', consultarResumenSensor);
    document.getElementById('btn-evaluar-sensor')?.addEventListener('click', evaluarSensor);
});