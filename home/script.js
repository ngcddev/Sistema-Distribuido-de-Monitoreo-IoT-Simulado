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
    document.getElementById('btn-get-total').addEventListener('click', consultarTotal);
    document.getElementById('btn-get-id').addEventListener('click', consultarPorId);
    document.getElementById('btn-post').addEventListener('click', function () { enviarMedicion('POST'); });
    document.getElementById('btn-put').addEventListener('click', function () { enviarMedicion('PUT'); });
    document.getElementById('btn-patch').addEventListener('click', function () { enviarMedicion('PATCH'); });
    document.getElementById('btn-delete').addEventListener('click', function () { enviarMedicion('DELETE'); });
});
