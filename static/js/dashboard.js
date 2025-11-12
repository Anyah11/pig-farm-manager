// ==========================================
// DASHBOARD.JS - Dashboard functionality
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeTableSorting();
    initializeExportButton();
    animateCounters();
});

// Real-time table search
function initializeSearch() {
    const table = document.querySelector('table tbody');
    if (!table) return;
    
    const cardHeader = document.querySelector('.card-header');
    if (!cardHeader) return;
    
    const searchHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0">All Pigs</h5>
            <div class="input-group" style="max-width: 300px;">
                <span class="input-group-text"><i class="bi bi-search"></i></span>
                <input type="text" id="pigSearch" class="form-control" placeholder="Search pigs...">
            </div>
        </div>
    `;
    cardHeader.innerHTML = searchHTML;
    
    // Search functionality
    document.getElementById('pigSearch').addEventListener('keyup', function() {
        const searchValue = this.value.toLowerCase();
        const rows = table.querySelectorAll('tr');
        let visibleCount = 0;
        
        rows.forEach(row => {
            if (row.querySelector('td[colspan]')) return; // Skip "no data" row
            
            const text = row.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
        
        // Show "no results" message if needed
        if (visibleCount === 0 && searchValue !== '') {
            if (!document.getElementById('noResults')) {
                const noResultsRow = document.createElement('tr');
                noResultsRow.id = 'noResults';
                noResultsRow.innerHTML = `
                    <td colspan="7" class="text-center text-muted py-4">
                        <i class="bi bi-search" style="font-size: 2rem;"></i><br>
                        No pigs found matching "${searchValue}"
                    </td>
                `;
                table.appendChild(noResultsRow);
            }
        } else {
            const noResults = document.getElementById('noResults');
            if (noResults) noResults.remove();
        }
    });
}

// Table sorting
function initializeTableSorting() {
    const headers = document.querySelectorAll('thead th');
    
    headers.forEach((header, index) => {
        if (index < headers.length - 1) { // Skip "Actions" column
            header.style.cursor = 'pointer';
            header.classList.add('sortable');
            header.innerHTML += ' <i class="bi bi-chevron-expand sort-icon" style="font-size: 0.7rem; opacity: 0.5;"></i>';
            
            header.addEventListener('click', function() {
                sortTable(index, this);
            });
        }
    });
}

function sortTable(columnIndex, headerElement) {
    const table = document.querySelector('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Don't sort if "no pigs" message is showing
    if (rows[0]?.querySelector('td[colspan]')) return;
    
    // Determine sort direction
    const isAscending = headerElement.classList.contains('sort-asc');
    
    // Remove all sort classes
    document.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.className = 'bi bi-chevron-expand sort-icon';
    });
    
    // Add appropriate class
    if (isAscending) {
        headerElement.classList.add('sort-desc');
        headerElement.querySelector('.sort-icon').className = 'bi bi-chevron-down sort-icon';
    } else {
        headerElement.classList.add('sort-asc');
        headerElement.querySelector('.sort-icon').className = 'bi bi-chevron-up sort-icon';
    }
    
    // Sort rows
    rows.sort((a, b) => {
        const aValue = a.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        const bValue = b.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        
        // Check if numeric
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? bNum - aNum : aNum - bNum;
        }
        
        // String comparison
        return isAscending ? 
            bValue.localeCompare(aValue) : 
            aValue.localeCompare(bValue);
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

// Export button animation
function initializeExportButton() {
    const exportLink = document.querySelector('a[href*="export_csv"]');
    if (!exportLink) return;
    
    exportLink.addEventListener('click', function(e) {
        const originalHTML = this.innerHTML;
        this.innerHTML = '<i class="bi bi-hourglass-split"></i> Exporting...';
        this.classList.add('disabled');
        this.style.pointerEvents = 'none';
        
        setTimeout(() => {
            this.innerHTML = originalHTML;
            this.classList.remove('disabled');
            this.style.pointerEvents = 'auto';
        }, 1500);
    });
}

// Animate stat counters
function animateCounters() {
    const counters = document.querySelectorAll('.card h2, .card h3');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent);
        if (isNaN(target)) return;
        
        const duration = 1000; // 1 second
        const increment = target / (duration / 16); // 60fps
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, 16);
    });
}

// Filter by status
function filterByStatus(status) {
    const rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        if (status === 'ALL') {
            row.style.display = '';
        } else {
            const badge = row.querySelector('.badge');
            if (badge && badge.textContent.trim() === status) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}