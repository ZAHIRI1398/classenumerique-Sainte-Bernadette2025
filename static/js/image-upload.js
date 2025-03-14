document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('image-preview');
    const dropZone = document.getElementById('image-dropzone');
    const annotationSection = document.getElementById('image-annotation-section');

    // Fonction pour afficher l'aperçu de l'image
    function displayImagePreview(file) {
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.innerHTML = `<img src="${e.target.result}" alt="Aperçu">`;
                dropZone.style.display = 'none';
                imagePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }

    // Gestionnaire pour le changement de fichier
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            if (file.type.match('image.*')) {
                displayImagePreview(file);
            } else {
                alert('Veuillez sélectionner une image valide.');
                imageInput.value = '';
            }
        }
    });

    // Gestionnaires pour le glisser-déposer
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type.match('image.*')) {
            imageInput.files = e.dataTransfer.files;
            displayImagePreview(file);
        } else {
            alert('Veuillez déposer une image valide.');
        }
    });

    // Gestionnaire pour le clic sur la zone de dépôt
    dropZone.addEventListener('click', function() {
        imageInput.click();
    });
});
