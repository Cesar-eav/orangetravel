// static/js/admin_tour_warning.js
document.addEventListener('DOMContentLoaded', function() {
    const nombreInput = document.querySelector('#id_nombre');
    const slugInput = document.querySelector('#id_slug');
    const warningId = 'nombre-change-warning';
    
    // Función para convertir texto a slug (formato URL)
    const slugify = (text) => {
        return text.toString().toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Quita acentos
            .replace(/\s+/g, '-')           // Reemplaza espacios con -
            .replace(/[^\w\-]+/g, '')       // Quita caracteres no permitidos
            .replace(/\-\-+/g, '-')         // Quita guiones dobles
            .replace(/^-+/, '')             // Quita guiones al inicio
            .replace(/-+$/, '');            // Quita guiones al final
    };

    if (nombreInput && slugInput) {
        const isEditing = !!slugInput.value; 

        if (isEditing) {
            // 1. Estado inicial: Bloqueado
            slugInput.readOnly = true;
            slugInput.style.backgroundColor = '#f3f4f6';

            // 2. Inyectamos el Checkbox (Si no existe ya)
            if (!document.getElementById('unlock-slug-checkbox')) {
                const container = document.createElement('div');
                container.style.cssText = 'margin-top: 10px; padding: 10px; border: 1px dashed #f97316; background: #fff8ed; border-radius: 6px;';
                container.innerHTML = `
                    <input type="checkbox" id="unlock-slug-checkbox" style="margin-right: 8px;">
                    <label for="unlock-slug-checkbox" 
                    style="
                        color: #ea580c; 
                        font-weight: bold; 
                        cursor: pointer;
                        float: none;    /* <--- MATAMOS EL FLOAT AQUÍ */
                        width: auto;     /* <--- MATAMOS EL ANCHO DE 160PX */
                        display: inline; /* <--- ASEGURAMOS QUE NO SALTE DE LÍNEA */
                        
                        ">
                        🔗 Cambiar Slug
                    </label>
                `;
                slugInput.parentNode.appendChild(container);
            }

            const checkbox = document.getElementById('unlock-slug-checkbox');

            // 3. LA MAGIA: Escuchar el cambio en el nombre
            nombreInput.addEventListener('input', function() {
                // Si el checkbox está marcado, el slug sigue al nombre en tiempo real
                if (checkbox.checked) {
                    slugInput.value = slugify(this.value);
                }
            });

            // 4. Gestión del Checkbox
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    const confirmacion = confirm('¿Quieres que el slug se genere automáticamente según el nombre? Esto cambiará la URL del tour.');
                    if (confirmacion) {
                        slugInput.readOnly = false;
                        slugInput.style.backgroundColor = '#ffffff';
                        // Generamos el slug actual de inmediato al marcar
                        slugInput.value = slugify(nombreInput.value);
                    } else {
                        this.checked = false;
                    }
                } else {
                    slugInput.readOnly = true;
                    slugInput.style.backgroundColor = '#f3f4f6';
                }
            });
        }
    }
});