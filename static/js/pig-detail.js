// ==========================================
// PIG-DETAIL.JS - Pig detail page functionality
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    setupWeightForm();
    setupSlaughterForm();
    highlightRecentWeight();
});

// Weight form enhancements
function setupWeightForm() {
    const weightForm = document.querySelector('form[action*="weigh"]');
    if (!weightForm) return;
    
    const weightInput = weightForm.querySelector('#weight');
    const dateInput = weightForm.querySelector('#date');
    const submitBtn = weightForm.querySelector('button[type="submit"]');
    
    // Set today's date
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    
    // Loading state on submit
    weightForm.addEventListener('submit', function(e) {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
        submitBtn.disabled = true;
    });
    
    // Weight input validation
    weightInput.addEventListener('input', function() {
        const value = parseFloat(this.value);
        
        if (value < 0) {
            this.value = 0;
        }
        
        if (value > 500) {
            if (!document.getElementById('weight-warning')) {
                const warning = document.createElement('small');
                warning.id = 'weight-warning';
                warning.className = 'form-text text-warning';
                warning.innerHTML = '<i class="bi bi-exclamation-triangle"></i> That\'s a very heavy pig!';
                this.parentElement.appendChild(warning);
            }
        } else {
            const warning = document.getElementById('weight-warning');
            if (warning) warning.remove();
        }
    });
}

// Slaughter form enhancements
function setupSlaughterForm() {
    const slaughterForm = document.querySelector('form[action*="slaughter"]');
    if (!slaughterForm) return;
    
    const killDateInput = slaughterForm.querySelector('#kill_date');
    const today = new Date().toISOString().split('T')[0];
    killDateInput.value = today;
    
    slaughterForm.addEventListener('submit', function(e) {
        const confirmMsg = `Are you absolutely sure you want to mark this pig as slaughtered?\n\nThis action cannot be undone.`;
        
        if (!confirm(confirmMsg)) {
            e.preventDefault();
        }
    });
}

// Highlight most recent weight entry
function highlightRecentWeight() {
    const rows = document.querySelectorAll('.table tbody tr');
    if (rows.length === 0) return;
    
    const firstRow = rows[0];
    if (!firstRow.querySelector('td[colspan]')) { // Not "no data" row
        firstRow.style.backgroundColor = '#f0f9ff';
        firstRow.style.fontWeight = '500';
        
        // Add "Latest" badge
        const weightCell = firstRow.querySelector('td:last-child');
        if (weightCell) {
            weightCell.innerHTML += ' <span class="badge bg-info">Latest</span>';
        }
    }
}

// Calculate weight gain/loss
function calculateWeightChange() {
    const rows = Array.from(document.querySelectorAll('.table tbody tr'));
    if (rows.length < 2) return;
    
    for (let i = 0; i < rows.length - 1; i++) {
        const currentRow = rows[i];
        const previousRow = rows[i + 1];
        
        if (currentRow.querySelector('td[colspan]') || previousRow.querySelector('td[colspan]')) continue;
        
        const currentWeight = parseFloat(currentRow.querySelectorAll('td')[1].textContent);
        const previousWeight = parseFloat(previousRow.querySelectorAll('td')[1].textContent);
        
        const change = currentWeight - previousWeight;
        const changePercent = ((change / previousWeight) * 100).toFixed(1);
        
        const weightCell = currentRow.querySelectorAll('td')[1];
        
        let changeHTML = '';
        if (change > 0) {
            changeHTML = `<br><small class="text-success"><i class="bi bi-arrow-up"></i> +${change.toFixed(1)}kg (${changePercent}%)</small>`;
        } else if (change < 0) {
            changeHTML = `<br><small class="text-danger"><i class="bi bi-arrow-down"></i> ${change.toFixed(1)}kg (${changePercent}%)</small>`;
        }
        
        weightCell.innerHTML += changeHTML;
    }
}

// Auto-calculate weight change if there are multiple entries
document.addEventListener('DOMContentLoaded', function() {
    const rows = document.querySelectorAll('.table tbody tr');
    if (rows.length > 1 && !rows[0].querySelector('td[colspan]')) {
        calculateWeightChange();
    }
});