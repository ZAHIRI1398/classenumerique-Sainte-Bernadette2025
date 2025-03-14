document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - exercise_form.js');
    const exerciseType = document.getElementById('exercise_type');
    if (!exerciseType) {
        console.error('Exercise type select not found');
        return;
    }
    console.log('Exercise type select found');

    // Créer les conteneurs pour chaque type d'exercice
    const exerciseTypeContainer = document.getElementById('exercise-type-container');
    if (!exerciseTypeContainer) {
        console.error('Exercise type container not found');
        return;
    }
    console.log('Exercise type container found');

    // Gérer le changement de type d'exercice
    exerciseType.addEventListener('change', function() {
        console.log('Exercise type changed to:', this.value);
        
        // Supprimer le contenu précédent
        exerciseTypeContainer.innerHTML = '';
        
        // Créer le nouveau contenu en fonction du type
        switch(this.value) {
            case 'qcm':
                exerciseTypeContainer.appendChild(createQCMForm());
                break;
            case 'mots_a_placer':
                exerciseTypeContainer.appendChild(createTextHolesForm());
                break;
            case 'vrai_faux':
                exerciseTypeContainer.appendChild(createTrueFalseForm());
                break;
            case 'texte_libre':
                exerciseTypeContainer.appendChild(createFreeTextForm());
                break;
            case 'correspondance':
                exerciseTypeContainer.appendChild(createMatchingForm());
                break;
            case 'ordre':
                exerciseTypeContainer.appendChild(createOrderingForm());
                break;
            case 'calcul':
                exerciseTypeContainer.appendChild(createCalculationForm());
                break;
            case 'dessin':
                exerciseTypeContainer.appendChild(createDrawingForm());
                break;
        }
    });

    // Déclencher l'événement change pour initialiser l'affichage
    exerciseType.dispatchEvent(new Event('change'));
});

function createQCMForm() {
    const container = document.createElement('div');
    container.className = 'qcm-form';
    
    const addQuestionBtn = document.createElement('button');
    addQuestionBtn.type = 'button';
    addQuestionBtn.className = 'btn btn-secondary mb-3';
    addQuestionBtn.innerHTML = '<i class="fas fa-plus"></i> Ajouter une question';
    
    const questionsList = document.createElement('div');
    questionsList.className = 'questions-list';
    
    container.appendChild(questionsList);
    container.appendChild(addQuestionBtn);
    
    let questionCounter = 0;
    
    function addQuestion() {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'card mb-3';
        questionDiv.innerHTML = `
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label">Question</label>
                    <input type="text" class="form-control" name="questions[][text]" required>
                </div>
                <div class="choices-list mb-3">
                    ${Array(4).fill(0).map((_, i) => `
                        <div class="input-group mb-2">
                            <input type="text" class="form-control" 
                                   name="questions[${questionCounter}][choices][][text]" 
                                   placeholder="Réponse ${i + 1}" required>
                            <div class="input-group-text">
                                <input class="form-check-input" type="radio" 
                                       name="questions[${questionCounter}][correct]" 
                                       value="${i}" ${i === 0 ? 'checked' : ''}>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <button type="button" class="btn btn-danger btn-sm remove-question">
                    <i class="fas fa-trash"></i> Supprimer
                </button>
            </div>
        `;
        
        questionDiv.querySelector('.remove-question').addEventListener('click', () => {
            questionDiv.remove();
        });
        
        questionsList.appendChild(questionDiv);
        questionCounter++;
    }
    
    addQuestionBtn.addEventListener('click', addQuestion);
    addQuestion(); // Ajouter une première question
    
    return container;
}

function createTextHolesForm() {
    const container = document.createElement('div');
    container.className = 'text-holes-form';
    container.innerHTML = `
        <div class="mb-3">
            <label class="form-label">Texte avec trous</label>
            <div class="alert alert-info">
                Pour créer un trou, entourez le mot avec des crochets. Exemple: Le [chat] dort sur le [canapé].
            </div>
            <textarea class="form-control" name="text_with_holes" rows="5" required></textarea>
        </div>
    `;
    return container;
}

function createTrueFalseForm() {
    const container = document.createElement('div');
    container.className = 'true-false-form';
    
    const addStatementBtn = document.createElement('button');
    addStatementBtn.type = 'button';
    addStatementBtn.className = 'btn btn-secondary mb-3';
    addStatementBtn.innerHTML = '<i class="fas fa-plus"></i> Ajouter une affirmation';
    
    const statementsList = document.createElement('div');
    statementsList.className = 'statements-list';
    
    container.appendChild(statementsList);
    container.appendChild(addStatementBtn);
    
    let statementCounter = 0;
    
    function addStatement() {
        const statementDiv = document.createElement('div');
        statementDiv.className = 'card mb-3';
        statementDiv.innerHTML = `
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label">Affirmation</label>
                    <input type="text" class="form-control" name="statements-${statementCounter}-text" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Réponse correcte</label>
                    <select class="form-select" name="statements-${statementCounter}-correct">
                        <option value="true">Vrai</option>
                        <option value="false">Faux</option>
                    </select>
                </div>
                <button type="button" class="btn btn-danger btn-sm remove-statement">
                    <i class="fas fa-trash"></i> Supprimer
                </button>
            </div>
        `;
        
        statementDiv.querySelector('.remove-statement').addEventListener('click', () => {
            statementDiv.remove();
        });
        
        statementsList.appendChild(statementDiv);
        statementCounter++;
    }
    
    addStatementBtn.addEventListener('click', addStatement);
    addStatement(); // Ajouter une première affirmation
    
    return container;
}

function createFreeTextForm() {
    const container = document.createElement('div');
    container.className = 'free-text-form';
    container.innerHTML = `
        <div class="mb-3">
            <label class="form-label">Question</label>
            <textarea class="form-control" name="free_text_question" rows="3" required></textarea>
        </div>
        <div class="mb-3">
            <label class="form-label">Mots-clés attendus (séparés par des virgules)</label>
            <input type="text" class="form-control" name="keywords" 
                   placeholder="mot1, mot2, mot3" required>
        </div>
    `;
    return container;
}

function createMatchingForm() {
    const container = document.createElement('div');
    container.className = 'matching-form';
    
    const addPairBtn = document.createElement('button');
    addPairBtn.type = 'button';
    addPairBtn.className = 'btn btn-secondary mb-3';
    addPairBtn.innerHTML = '<i class="fas fa-plus"></i> Ajouter une paire';
    
    const pairsList = document.createElement('div');
    pairsList.className = 'pairs-list';
    
    container.appendChild(pairsList);
    container.appendChild(addPairBtn);
    
    let pairCounter = 0;
    
    function addPair() {
        const pairDiv = document.createElement('div');
        pairDiv.className = 'card mb-3';
        pairDiv.innerHTML = `
            <div class="card-body">
                <div class="row">
                    <div class="col-md-5">
                        <label class="form-label">Élément gauche</label>
                        <input type="text" class="form-control" name="pairs-${pairCounter}-left" required>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Élément droit</label>
                        <input type="text" class="form-control" name="pairs-${pairCounter}-right" required>
                    </div>
                    <div class="col-md-2">
                        <button type="button" class="btn btn-danger btn-sm remove-pair">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        pairDiv.querySelector('.remove-pair').addEventListener('click', () => {
            pairDiv.remove();
        });
        
        pairsList.appendChild(pairDiv);
        pairCounter++;
    }
    
    addPairBtn.addEventListener('click', addPair);
    addPair(); // Ajouter une première paire
    
    return container;
}

function createOrderingForm() {
    const container = document.createElement('div');
    container.className = 'ordering-form';
    
    const addItemBtn = document.createElement('button');
    addItemBtn.type = 'button';
    addItemBtn.className = 'btn btn-secondary mb-3';
    addItemBtn.innerHTML = '<i class="fas fa-plus"></i> Ajouter un élément';
    
    const itemsList = document.createElement('div');
    itemsList.className = 'items-list';
    
    container.appendChild(itemsList);
    container.appendChild(addItemBtn);
    
    let itemCounter = 0;
    
    function addItem() {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'card mb-3';
        itemDiv.innerHTML = `
            <div class="card-body">
                <div class="row">
                    <div class="col-md-10">
                        <label class="form-label">Élément ${itemCounter + 1}</label>
                        <input type="text" class="form-control" name="order_items-${itemCounter}" required>
                    </div>
                    <div class="col-md-2">
                        <button type="button" class="btn btn-danger btn-sm remove-item">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        itemDiv.querySelector('.remove-item').addEventListener('click', () => {
            itemDiv.remove();
        });
        
        itemsList.appendChild(itemDiv);
        itemCounter++;
    }
    
    addItemBtn.addEventListener('click', addItem);
    addItem(); // Ajouter un premier élément
    
    return container;
}

function createCalculationForm() {
    const container = document.createElement('div');
    container.className = 'calculation-form';
    container.innerHTML = `
        <div class="mb-3">
            <label class="form-label">Expression mathématique</label>
            <input type="text" class="form-control" name="calculation_expression" 
                   placeholder="Ex: 2x + 3 = 10" required>
        </div>
        <div class="mb-3">
            <label class="form-label">Solution</label>
            <input type="text" class="form-control" name="calculation_solution" 
                   placeholder="Ex: x = 3.5" required>
        </div>
    `;
    return container;
}

function createDrawingForm() {
    const container = document.createElement('div');
    container.className = 'drawing-form';
    container.innerHTML = `
        <div class="mb-3">
            <label class="form-label">Instructions de dessin</label>
            <textarea class="form-control" name="drawing_instructions" rows="4" required
                      placeholder="Ex: Dessiner un triangle rectangle de côtés 3cm, 4cm et 5cm"></textarea>
        </div>
        <div class="mb-3">
            <label class="form-label">Points de validation (coordonnées x,y séparées par des virgules)</label>
            <input type="text" class="form-control" name="validation_points" 
                   placeholder="Ex: 0,0; 3,0; 0,4" required>
        </div>
    `;
    return container;
}
