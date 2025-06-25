/**
 * Client List Management JavaScript
 * Handles filtering, sorting, and client actions
 */

class ClientListManager {
    constructor() {
        this.config = window.INVOICING_CONFIG || {};
        this.elements = {
            searchInput: document.getElementById('clientSearch'),
            statusFilter: document.getElementById('statusFilter'),
            sortFilter: document.getElementById('sortFilter'),
            clearFiltersBtn: document.getElementById('clearFilters'),
            clientRows: document.querySelectorAll('.client-row'),
            clientCount: document.getElementById('clientCount'),
            tableBody: document.getElementById('clientsTableBody'),
            emptyState: document.getElementById('emptyState')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeTooltips();
        console.log('Client List Manager initialized');
    }

    bindEvents() {
        // Search and filter events
        this.elements.searchInput?.addEventListener('input', 
            this.debounce(() => this.filterClients(), 300)
        );
        
        this.elements.statusFilter?.addEventListener('change', () => this.filterClients());
        this.elements.sortFilter?.addEventListener('change', () => this.sortClients());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());

        // Table sorting
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', (e) => this.handleSort(e));
        });

        // FIXED: Use event delegation for client actions
        document.addEventListener('click', (e) => {
            // Only handle delete buttons with data-client-id attribute
            if (e.target.closest('[data-client-id][data-action="delete"]')) {
                e.preventDefault();
                this.handleDeleteClient(e.target.closest('[data-client-id][data-action="delete"]'));
            } else if (e.target.closest('[data-client-id][data-action="edit"]')) {
                e.preventDefault();
                this.handleEditClient(e.target.closest('[data-client-id][data-action="edit"]'));
            } else if (e.target.closest('[data-client-id][data-action="view"]')) {
                e.preventDefault();
                this.handleViewClient(e.target.closest('[data-client-id][data-action="view"]'));
            }
        });

        // Dropdown toggles
        document.querySelectorAll('.oh-dropdown__toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => this.toggleDropdown(e));
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => this.closeDropdowns(e));
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    filterClients() {
        const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
        const statusValue = this.elements.statusFilter?.value || '';
        
        let visibleCount = 0;
        
        this.elements.clientRows.forEach(row => {
            let show = true;
            
            // Search filter
            if (searchTerm) {
                const name = row.dataset.name || '';
                const email = row.dataset.email || '';
                const contact = row.dataset.contact || '';
                
                if (!name.includes(searchTerm) && 
                    !email.includes(searchTerm) && 
                    !contact.includes(searchTerm)) {
                    show = false;
                }
            }
            
            // Status filter
            if (statusValue && row.dataset.status !== statusValue) {
                show = false;
            }
            
            // Apply filter with animation
            if (show) {
                row.style.display = '';
                row.classList.remove('filtered-out');
                visibleCount++;
            } else {
                row.classList.add('filtered-out');
                setTimeout(() => {
                    if (row.classList.contains('filtered-out')) {
                        row.style.display = 'none';
                    }
                }, 200);
            }
        });
        
        // Update count
        this.updateClientCount(visibleCount);
        
        // Show/hide empty state
        this.toggleEmptyState(visibleCount === 0);
    }

    sortClients() {
        const sortBy = this.elements.sortFilter?.value || 'name';
        const rows = Array.from(this.elements.clientRows);
        
        rows.sort((a, b) => {
            let aVal = '';
            let bVal = '';
            
            switch(sortBy) {
                case 'name':
                    aVal = a.dataset.name || '';
                    bVal = b.dataset.name || '';
                    break;
                case 'email':
                    aVal = a.dataset.email || '';
                    bVal = b.dataset.email || '';
                    break;
                case 'contact':
                    aVal = a.dataset.contact || '';
                    bVal = b.dataset.contact || '';
                    break;
                default:
                    return 0;
            }
            
            return aVal.localeCompare(bVal);
        });
        
        // Reorder DOM with animation
        this.elements.tableBody?.classList.add('loading');
        
        setTimeout(() => {
            rows.forEach(row => this.elements.tableBody?.appendChild(row));
            this.elements.tableBody?.classList.remove('loading');
        }, 150);
    }

    handleSort(event) {
        const header = event.currentTarget;
        const sortBy = header.dataset.sort;
        const isAscending = !header.classList.contains('sort-desc');
        
        // Remove sort classes from all headers
        document.querySelectorAll('.sortable').forEach(h => {
            h.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Add sort class to current header
        header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
        
        this.sortClientsByColumn(sortBy, isAscending);
    }

    sortClientsByColumn(sortBy, ascending = true) {
        const rows = Array.from(this.elements.clientRows);
        
        rows.sort((a, b) => {
            let aVal = a.dataset[sortBy] || '';
            let bVal = b.dataset[sortBy] || '';
            
            const result = aVal.localeCompare(bVal);
            return ascending ? result : -result;
        });
        
        // Reorder DOM
        rows.forEach(row => this.elements.tableBody?.appendChild(row));
    }

    clearFilters() {
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        
        this.filterClients();
        
        // Show success feedback
        this.showToast('Filters cleared', 'success');
    }

    handleDeleteClient(button) {
        const clientId = button.dataset.clientId;
        const clientName = button.closest('tr')?.querySelector('strong')?.textContent;
        
        if (confirm(`Are you sure you want to delete "${clientName}"? This action cannot be undone.`)) {
            this.deleteClient(clientId, clientName);
        }
    }

    handleEditClient(button) {
        const clientId = button.dataset.clientId;
        window.location.href = `/invoicing/clients/${clientId}/edit/`;
    }

    handleViewClient(button) {
        const clientId = button.dataset.clientId;
        window.location.href = `/invoicing/clients/${clientId}/`;
    }

    async deleteClient(clientId, clientName) {
        try {
            const response = await fetch(`/invoicing/clients/${clientId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove row with animation
                const row = document.querySelector(`[data-client-id="${clientId}"]`)?.closest('tr');
                if (row) {
                    row.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        row.remove();
                        this.updateClientCount();
                        this.showToast(data.message || `Client "${clientName}" deleted successfully`, 'success');
                    }, 300);
                }
            } else {
                this.showToast(data.message || 'Error deleting client', 'error');
            }
        } catch (error) {
            console.error('Error deleting client:', error);
            this.showToast('Error deleting client', 'error');
        }
    }

    toggleDropdown(event) {
        event.stopPropagation();
        const dropdown = event.currentTarget.closest('.oh-dropdown');
        
        // Close other dropdowns
        document.querySelectorAll('.oh-dropdown.active').forEach(d => {
            if (d !== dropdown) d.classList.remove('active');
        });
        
        dropdown.classList.toggle('active');
    }

    closeDropdowns(event) {
        if (!event.target.closest('.oh-dropdown')) {
            document.querySelectorAll('.oh-dropdown.active').forEach(d => {
                d.classList.remove('active');
            });
        }
    }

    updateClientCount(count = null) {
        if (!this.elements.clientCount) return;
        
        if (count === null) {
            count = document.querySelectorAll('.client-row:not([style*="display: none"])').length;
        }
        
        const text = this.config.translations?.clients || 'Clients';
        this.elements.clientCount.textContent = `${count} ${text}`;
    }

    toggleEmptyState(show) {
        if (this.elements.emptyState) {
            this.elements.emptyState.style.display = show ? 'block' : 'none';
        }
        
        if (this.elements.tableBody) {
            this.elements.tableBody.style.display = show ? 'none' : '';
        }
    }

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
            color: white;
            border-radius: 4px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    initializeTooltips() {
        // Add tooltips to action buttons
        document.querySelectorAll('[title]').forEach(element => {
            // Initialize tooltip library if available
            if (window.bootstrap?.Tooltip) {
                new bootstrap.Tooltip(element);
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ClientListManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: scale(1); }
        to { opacity: 0; transform: scale(0.95); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
