document.addEventListener('DOMContentLoaded', function() {
    const imagePreview = document.getElementById('image-preview');
    const annotationMarkers = document.getElementById('annotation-markers');
    const annotationsContainer = document.getElementById('annotations-container');
    const addAnnotationBtn = document.getElementById('add-annotation');
    const imageUploadSection = document.getElementById('image-annotation-section');

    let annotations = [];
    let isDragging = false;
    let selectedMarker = null;
    let currentScale = 1;
    let lastTouchDistance = 0;

    // Fonction pour initialiser le système d'annotation
    function initializeAnnotationSystem() {
        const img = imagePreview.querySelector('img');
        if (!img) return;

        // Ajuster la taille du conteneur des marqueurs
        function updateMarkersContainer() {
            const rect = img.getBoundingClientRect();
            annotationMarkers.style.width = rect.width + 'px';
            annotationMarkers.style.height = rect.height + 'px';
            annotationMarkers.style.transform = `scale(${currentScale})`;
        }

        // Mettre à jour la taille initiale
        updateMarkersContainer();

        // Mettre à jour la taille lors du redimensionnement
        window.addEventListener('resize', updateMarkersContainer);

        // Gestionnaire de clic sur l'image
        imagePreview.addEventListener('click', function(e) {
            if (isDragging || e.target.classList.contains('annotation-marker')) return;
            
            const rect = img.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            
            // Vérifier si le clic est bien sur l'image
            if (x >= 0 && x <= 100 && y >= 0 && y <= 100) {
                addAnnotation(x, y);
            }
        });

        // Support du zoom sur mobile
        img.addEventListener('touchstart', handleTouchStart, { passive: false });
        img.addEventListener('touchmove', handleTouchMove, { passive: false });
        img.addEventListener('touchend', handleTouchEnd, { passive: false });
    }

    // Observer les changements dans la section d'annotation d'image
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                if (imageUploadSection.style.display !== 'none') {
                    if (imagePreview.querySelector('img')) {
                        initializeAnnotationSystem();
                        loadExistingAnnotations();
                    }
                }
            }
        });
    });

    observer.observe(imageUploadSection, { attributes: true });

    // Observer les changements dans le conteneur d'aperçu d'image
    const imageObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && imagePreview.querySelector('img')) {
                initializeAnnotationSystem();
                loadExistingAnnotations();
            }
        });
    });

    imageObserver.observe(imagePreview, { childList: true });

    function createMarker(x, y, label, index) {
        const marker = document.createElement('div');
        marker.className = 'annotation-marker';
        marker.dataset.index = index;
        marker.style.left = x + '%';
        marker.style.top = y + '%';

        const labelEl = document.createElement('div');
        labelEl.className = 'annotation-label';
        labelEl.textContent = label;
        marker.appendChild(labelEl);

        // Ajout des gestionnaires d'événements tactiles
        marker.addEventListener('mousedown', startDragging);
        marker.addEventListener('touchstart', handleMarkerTouchStart, { passive: false });
        marker.addEventListener('touchmove', handleMarkerTouchMove, { passive: false });
        marker.addEventListener('touchend', stopDragging);

        return marker;
    }

    function createAnnotationItem(annotation, index) {
        const item = document.createElement('div');
        item.className = 'annotation-item';
        item.innerHTML = `
            <div class="annotation-text">
                <input type="text" class="form-control" value="${annotation.label}" 
                       placeholder="Entrez le texte de l'annotation" data-index="${index}">
            </div>
            <div class="btn-group">
                <button type="button" class="btn btn-outline-danger btn-sm remove-annotation" data-index="${index}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        const input = item.querySelector('input');
        input.addEventListener('input', (e) => {
            updateAnnotationLabel(index, e.target.value);
        });

        const removeBtn = item.querySelector('.remove-annotation');
        removeBtn.addEventListener('click', () => {
            removeAnnotation(index);
        });

        return item;
    }

    function addAnnotation(x, y) {
        const index = annotations.length;
        const annotation = {
            label: `Annotation ${index + 1}`,
            x: x,
            y: y
        };

        annotations.push(annotation);
        
        const marker = createMarker(x, y, annotation.label, index);
        annotationMarkers.appendChild(marker);

        const item = createAnnotationItem(annotation, index);
        annotationsContainer.appendChild(item);

        updateHiddenInput();
    }

    function updateAnnotationLabel(index, newLabel) {
        if (index >= 0 && index < annotations.length) {
            annotations[index].label = newLabel;
            const marker = annotationMarkers.querySelector(`[data-index="${index}"] .annotation-label`);
            if (marker) {
                marker.textContent = newLabel;
            }
            updateHiddenInput();
        }
    }

    function removeAnnotation(index) {
        const marker = annotationMarkers.querySelector(`[data-index="${index}"]`);
        if (marker) marker.remove();

        annotations.splice(index, 1);
        refreshAnnotationsList();
    }

    function refreshAnnotationsList() {
        annotationsContainer.innerHTML = '';
        annotationMarkers.innerHTML = '';
        
        annotations.forEach((annotation, index) => {
            const marker = createMarker(annotation.x, annotation.y, annotation.label, index);
            annotationMarkers.appendChild(marker);
            
            const item = createAnnotationItem(annotation, index);
            annotationsContainer.appendChild(item);
        });

        updateHiddenInput();
    }

    function startDragging(e) {
        if (e.target.closest('.annotation-marker')) {
            e.preventDefault();
            e.stopPropagation();
            isDragging = true;
            selectedMarker = e.target.closest('.annotation-marker');
            selectedMarker.style.cursor = 'grabbing';
            selectedMarker.classList.add('dragging');

            document.addEventListener('mousemove', handleDrag);
            document.addEventListener('mouseup', stopDragging);
        }
    }

    function handleDrag(e) {
        if (isDragging && selectedMarker) {
            e.preventDefault();
            const img = imagePreview.querySelector('img');
            const rect = img.getBoundingClientRect();
            
            let x = ((e.clientX - rect.left) / rect.width) * 100;
            let y = ((e.clientY - rect.top) / rect.height) * 100;
            
            x = Math.max(0, Math.min(100, x));
            y = Math.max(0, Math.min(100, y));
            
            selectedMarker.style.left = x + '%';
            selectedMarker.style.top = y + '%';
            
            const index = parseInt(selectedMarker.dataset.index);
            if (index >= 0 && index < annotations.length) {
                annotations[index].x = x;
                annotations[index].y = y;
                updateHiddenInput();
            }
        }
    }

    function stopDragging() {
        if (selectedMarker) {
            selectedMarker.style.cursor = '';
            selectedMarker.classList.remove('dragging');
        }
        isDragging = false;
        selectedMarker = null;
        document.removeEventListener('mousemove', handleDrag);
        document.removeEventListener('mouseup', stopDragging);
    }

    function handleMarkerTouchStart(e) {
        if (e.target.closest('.annotation-marker')) {
            e.preventDefault();
            isDragging = true;
            selectedMarker = e.target.closest('.annotation-marker');
            selectedMarker.classList.add('dragging');
        }
    }

    function handleMarkerTouchMove(e) {
        if (isDragging && selectedMarker && e.touches.length === 1) {
            e.preventDefault();
            const touch = e.touches[0];
            const img = imagePreview.querySelector('img');
            const rect = img.getBoundingClientRect();
            
            let x = ((touch.clientX - rect.left) / rect.width) * 100;
            let y = ((touch.clientY - rect.top) / rect.height) * 100;
            
            x = Math.max(0, Math.min(100, x));
            y = Math.max(0, Math.min(100, y));
            
            selectedMarker.style.left = x + '%';
            selectedMarker.style.top = y + '%';
            
            const index = parseInt(selectedMarker.dataset.index);
            if (index >= 0 && index < annotations.length) {
                annotations[index].x = x;
                annotations[index].y = y;
                updateHiddenInput();
            }
        }
    }

    function handleTouchStart(e) {
        if (e.touches.length === 2) {
            e.preventDefault();
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            lastTouchDistance = Math.hypot(
                touch2.clientX - touch1.clientX,
                touch2.clientY - touch1.clientY
            );
        }
    }

    function handleTouchMove(e) {
        if (e.touches.length === 2) {
            e.preventDefault();
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            const currentDistance = Math.hypot(
                touch2.clientX - touch1.clientX,
                touch2.clientY - touch1.clientY
            );

            if (lastTouchDistance > 0) {
                const scale = currentDistance / lastTouchDistance;
                currentScale *= scale;
                currentScale = Math.max(0.5, Math.min(3, currentScale));
                
                const img = imagePreview.querySelector('img');
                img.style.transform = `scale(${currentScale})`;
                annotationMarkers.style.transform = `scale(${currentScale})`;
            }

            lastTouchDistance = currentDistance;
        }
    }

    function handleTouchEnd() {
        lastTouchDistance = 0;
    }

    function loadExistingAnnotations() {
        const hiddenInput = document.querySelector('input[name="annotations"]');
        if (hiddenInput && hiddenInput.value) {
            try {
                annotations = JSON.parse(hiddenInput.value);
                refreshAnnotationsList();
            } catch (e) {
                console.error('Erreur lors du chargement des annotations:', e);
                annotations = [];
            }
        }
    }

    function updateHiddenInput() {
        const hiddenInput = document.querySelector('input[name="annotations"]');
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(annotations);
        }
    }

    // Gestionnaire pour le bouton d'ajout d'annotation
    addAnnotationBtn.addEventListener('click', () => {
        const img = imagePreview.querySelector('img');
        if (img) {
            const rect = img.getBoundingClientRect();
            addAnnotation(50, 50); // Ajouter au centre par défaut
        }
    });

    // Initialisation au chargement
    if (imagePreview.querySelector('img')) {
        initializeAnnotationSystem();
        loadExistingAnnotations();
    }
});
