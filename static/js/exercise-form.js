// Fonction pour créer un template de question QCM
function createQuestionTemplate(index) {
    return `
    <div class="card mb-3 question-card">
        <div class="card-body">
            <div class="mb-3">
                <label class="form-label">Question</label>
                <input type="text" class="form-control" name="questions-${index}-text" required>
            </div>
            <div class="choices">
                ${Array.from({length: 4}, (_, i) => `
                    <div class="choice-item mb-2">
                        <div class="input-group">
                            <input type="text" class="form-control" name="questions-${index}-choices-${i}-text" placeholder="Réponse" required>
                            <div class="input-group-text">
                                <input type="checkbox" class="form-check-input mt-0" name="questions-${index}-choices-${i}-is_correct">
                                <label class="form-check-label ms-2">Correcte</label>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
            <button type="button" class="btn btn-danger btn-sm mt-2 remove-question">
                <i class="fas fa-trash"></i> Supprimer la question
            </button>
        </div>
    </div>`;
}

// Fonction pour créer un template de trou
function createHoleTemplate(index) {
    return `
    <div class="card mb-3 hole-card">
        <div class="card-body">
            <div class="mb-3">
                <label class="form-label">Texte avant le trou</label>
                <textarea class="form-control" name="text_holes-${index}-text_before" rows="2" required></textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Mot à placer</label>
                <input type="text" class="form-control" name="text_holes-${index}-correct_answer" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Texte après le trou</label>
                <textarea class="form-control" name="text_holes-${index}-text_after" rows="2" required></textarea>
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-hole">
                <i class="fas fa-trash"></i> Supprimer le trou
            </button>
        </div>
    </div>`;
}

// Fonction pour créer un template de paire
function createPairTemplate(index) {
    return `
    <div class="card mb-3 pair-card">
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <h5>Élément gauche</h5>
                    <div class="mb-3">
                        <label class="form-label">Type</label>
                        <select class="form-select left-type" name="pair_matches-${index}-left_type" required>
                            <option value="text">Texte</option>
                            <option value="image">Image</option>
                        </select>
                    </div>
                    <div class="mb-3 left-content">
                        <label class="form-label">Contenu</label>
                        <input type="text" class="form-control" name="pair_matches-${index}-left_content">
                    </div>
                    <div class="mb-3 left-image" style="display: none;">
                        <div class="image-upload-container">
                            <label class="form-label">Image</label>
                            <div class="image-upload-dropzone">
                                <input type="file" class="form-control" name="pair_matches-${index}-left_image" accept="image/*">
                                <div class="upload-message">
                                    <i class="fas fa-cloud-upload-alt fa-2x mb-2"></i>
                                    <p>Glissez votre image ici ou cliquez pour sélectionner</p>
                                </div>
                            </div>
                            <div class="image-preview"></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h5>Élément droite</h5>
                    <div class="mb-3">
                        <label class="form-label">Type</label>
                        <select class="form-select right-type" name="pair_matches-${index}-right_type" required>
                            <option value="text">Texte</option>
                            <option value="image">Image</option>
                        </select>
                    </div>
                    <div class="mb-3 right-content">
                        <label class="form-label">Contenu</label>
                        <input type="text" class="form-control" name="pair_matches-${index}-right_content">
                    </div>
                    <div class="mb-3 right-image" style="display: none;">
                        <div class="image-upload-container">
                            <label class="form-label">Image</label>
                            <div class="image-upload-dropzone">
                                <input type="file" class="form-control" name="pair_matches-${index}-right_image" accept="image/*">
                                <div class="upload-message">
                                    <i class="fas fa-cloud-upload-alt fa-2x mb-2"></i>
                                    <p>Glissez votre image ici ou cliquez pour sélectionner</p>
                                </div>
                            </div>
                            <div class="image-preview"></div>
                        </div>
                    </div>
                </div>
            </div>
            <button type="button" class="btn btn-danger btn-sm mt-3 remove-pair">
                <i class="fas fa-trash"></i> Supprimer la paire
            </button>
        </div>
    </div>`;
}

document.addEventListener('DOMContentLoaded', function() {
    // Compteurs pour les indices
    let questionCounter = document.querySelectorAll('.question-card').length;
    let holeCounter = document.querySelectorAll('.hole-card').length;
    let pairCounter = document.querySelectorAll('.pair-card').length;

    // Ajouter une question QCM
    document.getElementById('add-qcm-question')?.addEventListener('click', function() {
        const questionsContainer = document.getElementById('qcm-questions');
        questionsContainer.insertAdjacentHTML('beforeend', createQuestionTemplate(questionCounter++));
    });

    // Ajouter un trou
    document.getElementById('add-hole')?.addEventListener('click', function() {
        const holesContainer = document.getElementById('holes-container');
        holesContainer.insertAdjacentHTML('beforeend', createHoleTemplate(holeCounter++));
    });

    // Ajouter une paire
    document.getElementById('add-pair')?.addEventListener('click', function() {
        const pairsContainer = document.getElementById('pair-matches');
        pairsContainer.insertAdjacentHTML('beforeend', createPairTemplate(pairCounter++));
        initializePairCard(pairsContainer.lastElementChild);
    });

    // Supprimer une question
    document.addEventListener('click', function(e) {
        if (e.target.matches('.remove-question')) {
            e.target.closest('.question-card').remove();
        }
    });

    // Supprimer un trou
    document.addEventListener('click', function(e) {
        if (e.target.matches('.remove-hole')) {
            e.target.closest('.hole-card').remove();
        }
    });

    // Supprimer une paire
    document.addEventListener('click', function(e) {
        if (e.target.matches('.remove-pair')) {
            e.target.closest('.pair-card').remove();
        }
    });

    // Initialiser les cartes de paires existantes
    document.querySelectorAll('.pair-card').forEach(initializePairCard);
});

// Fonction pour initialiser une carte de paire
function initializePairCard(card) {
    const leftType = card.querySelector('.left-type');
    const rightType = card.querySelector('.right-type');
    const leftContent = card.querySelector('.left-content');
    const leftImage = card.querySelector('.left-image');
    const rightContent = card.querySelector('.right-content');
    const rightImage = card.querySelector('.right-image');

    function updateContentVisibility(type, content, image) {
        if (type.value === 'text') {
            content.style.display = 'block';
            image.style.display = 'none';
        } else {
            content.style.display = 'none';
            image.style.display = 'block';
        }
    }

    leftType.addEventListener('change', () => {
        updateContentVisibility(leftType, leftContent, leftImage);
    });

    rightType.addEventListener('change', () => {
        updateContentVisibility(rightType, rightContent, rightImage);
    });

    // Initialiser la visibilité
    updateContentVisibility(leftType, leftContent, leftImage);
    updateContentVisibility(rightType, rightContent, rightImage);

    // Initialiser le glisser-déposer pour les images
    initializeImageUpload(card);
}

// Fonction pour initialiser le glisser-déposer des images
function initializeImageUpload(card) {
    card.querySelectorAll('.image-upload-dropzone').forEach(dropzone => {
        const input = dropzone.querySelector('input[type="file"]');
        const preview = dropzone.closest('.image-upload-container').querySelector('.image-preview');

        // Gérer le glisser-déposer
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                handleImageUpload(input.files[0], preview);
            }
        });

        // Gérer la sélection de fichier
        input.addEventListener('change', () => {
            if (input.files.length) {
                handleImageUpload(input.files[0], preview);
            }
        });
    });
}

// Fonction pour gérer l'upload d'image
function handleImageUpload(file, preview) {
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.style.backgroundImage = `url(${e.target.result})`;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}
