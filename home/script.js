// Esperamos a que todo el HTML cargue correctamente
document.addEventListener('DOMContentLoaded', () => {
    
    // Capturamos el botón y el texto de estado por su ID
    const btnConectar = document.getElementById('btn-conectar');
    const statusText = document.getElementById('status');

    // Le agregamos un evento al hacer clic en el botón
    btnConectar.addEventListener('click', () => {
        
        // 1. Estado de carga (Mientras "conecta" con Python)
        btnConectar.disabled = true;
        btnConectar.textContent = 'Conectando al Backend...';
        statusText.style.color = '#d97706'; // Naranja/Dorado para espera
        statusText.textContent = 'Ejecutando petición GET hacia los servicios... ⏳';

        // 2. Simulamos un tiempo de respuesta de red de 2 segundos (2000 ms)
        setTimeout(() => {
            // Obtenemos la hora exacta para que se vea muy real
            const horaActual = new Date().toLocaleTimeString();

            // 3. Estado de éxito (Cuando "llegan" los datos)
            btnConectar.disabled = false;
            btnConectar.textContent = 'Probar Nueva Conexión';
            statusText.style.color = '#10b981'; // Verde para éxito
            statusText.innerHTML = `✅ <strong>200 OK</strong>: Conexión exitosa. <br> Último chequeo: ${horaActual}`;
            
            /* 
               NOTA PARA EL EQUIPO: 
               Cuando la API de Python esté lista, se reemplazará este 
               'setTimeout' por la función real: fetch('URL_DEL_BACKEND')
            */
            
        }, 2000);
    });
});