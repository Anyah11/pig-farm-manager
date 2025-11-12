// ==========================================
// FORMS.JS - Form validation and helpers
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeFormValidation();
    setupPigIdFormatter();
    setupDateDefaults();
});

// Real-time form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required], select[required]');
        
        inputs.forEach(input => {
            // Validation on blur
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            // Remove error on input
            input.addEventListener('input', function() {
                if (this.value.trim() !== '') {
                    this.classList.remove('is-invalid');
                }
            });
        });
        
        // Form submission validation
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            inputs.forEach(input => {
                if (!validateField(input)) {
                    isValid = false;
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showToast('Please fill in all required fields', 'danger');
                
                // Focus first invalid field
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });
}

function validateField(field) {
    if (field.hasAttribute('required') && field.value.trim() === '') {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        return false;
    } else if (field.value.trim() !== '') {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
        return true;
    }
    return true;
}

// Auto-format Pig ID to uppercase
function setupPigIdFormatter() {
    const pigIdInput = document.getElementById('pig_id');
    if (!pigIdInput) return;
    
    pigIdInput.addEventListener('input', function() {
        this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    });
    
    // Auto-focus
    pigIdInput.focus();
    
    // Add hint
    const hint = document.createElement('small');
    hint.className = 'form-text text-muted';
    hint.innerHTML = '<i class="bi bi-info-circle"></i> Only letters and numbers, automatically converted to uppercase';
    pigIdInput.parentElement.appendChild(hint);
}

// Set today's date as default for date inputs
function setupDateDefaults() {
    const today = new Date().toISOString().split('T')[0];
    
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value && input.id !== 'dob') { // Don't set default for DOB
            input.value = today;
        }
    });
}

// Weight input validation (only positive numbers)
document.addEventListener('DOMContentLoaded', function() {
    const weightInput = document.getElementById('weight');
    if (!weightInput) return;
    
    weightInput.addEventListener('input', function() {
        // Remove negative values
        if (this.value < 0) {
            this.value = Math.abs(this.value);
        }
        
        // Limit to 2 decimal places
        if (this.value.includes('.')) {
            const parts = this.value.split('.');
            if (parts[1].length > 1) {
                this.value = parseFloat(this.value).toFixed(1);
            }
        }
    });
});

// Character counter for text inputs
function addCharacterCounter(inputId, maxLength) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    input.setAttribute('maxlength', maxLength);
    
    const counter = document.createElement('small');
    counter.className = 'form-text text-muted character-counter';
    counter.textContent = `0 / ${maxLength}`;
    input.parentElement.appendChild(counter);
    
    input.addEventListener('input', function() {
        counter.textContent = `${this.value.length} / ${maxLength}`;
        
        if (this.value.length > maxLength * 0.9) {
            counter.classList.add('text-warning');
        } else {
            counter.classList.remove('text-warning');
        }
    });
}