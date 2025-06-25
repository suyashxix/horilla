/**
 * Placement List Management JavaScript
 * Handles filtering, sorting, and placement actions
 */

class PlacementListManager {
    constructor() {
        this.config = window.PLACEMENT_CONFIG || {};
        this.elements = {
            searchInput: document.getElementById('placementSearch'),
            statusFilter: document.getElementById('statusFilter'),
            clientFilter: document.getElementById('clientFilter'),
            sortFilter: document.getElementById('sortFilter'),
            clearFiltersBtn: document.getElementById('clearFilters'),
            clearSearchBtn: document.getElementById('clearSearchBtn'),
            placementCards: document.querySelectorAll('.placement-card'),
            placementCount: document.getElementById('placementCount'),
            placementsList: document.getElementById('placementsList'),
            noResultsMessage: document.getElementById('noResultsMessage'),
            emptyState: document.getElementById('emptyState')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateStats();
        this.initializeTooltips();
        console.log('Placement List Manager initialized');
    }

    bindEvents() {
        // Search and filter events
        this.elements.searchInput?.addEventListener('input', 
            this.debounce(() => this.filterPlacements(), 300)
        );
        
        this.elements.statusFilter?.addEventListener('change', () => this.filterPlacements());
        this.elements.clientFilter?.addEventListener('change', () => this.filterPlacements());
        this.elements.sortFilter?.addEventListener('change', () => this.sortPlacements());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.elements.clearSearchBtn?.addEventListener('click', () => this.clearFilters());

        // Placement action buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="delete"]')) {
                e.preventDefault();
                this.handleDeletePlacement(e.target.closest('[data-action="delete"]'));
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

    filterPlacements() {
        const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
        const statusValue = this.elements.statusFilter?.value || '';
        const clientValue = this.elements.clientFilter?.value || '';
        
        let visibleCount = 0;
        
        this.elements.placementCards.forEach(card => {
            let show = true;
            
            // Search filter
            if (searchTerm) {
                const candidate = card.dataset.candidate || '';
                const client = card.dataset.client || '';
                const position = card.dataset.position || '';
                
                if (!candidate.includes(searchTerm) && 
                    !client.includes(searchTerm) && 
                    !position.includes(searchTerm)) {
                    show = false;
                }
            }
            
            // Status filter
            if (statusValue && card.dataset.status !== statusValue) {
                show = false;
            }
            
            // Client filter
            if (clientValue && card.dataset.client !== clientValue) {
                show = false;
            }
            
            // Apply filter with animation
            if (show) {
                card.style.display = '';
                card.classList.remove('filtered-out');
                visibleCount++;
            } else {
                card.classList.add('filtered-out');
                setTimeout(() => {
                    if (card.classList.contains('filtered-out')) {
                        card.style.display = 'none';
                    }
                }, 200);
            }
        });
        
        // Update count and visibility
        this.updatePlacementCount(visibleCount);
        this.toggleNoResultsMessage(visibleCount === 0);
        this.updateStats();
    }

    sortPlacements() {
        const sortBy = this.elements.sortFilter?.value || 'joining_date';
        const cards = Array.from(this.elements.placementCards);
        
        cards.sort((a, b) => {
            let aVal = '';
            let bVal = '';
            
            switch(sortBy) {
                case 'candidate':
                    aVal = a.dataset.candidate || '';
                    bVal = b.dataset.candidate || '';
                    break;
                case 'client':
                    aVal = a.dataset.client || '';
                    bVal = b.dataset.client || '';
                    break;
                case 'position':
                    aVal = a.dataset.position || '';
                    bVal = b.dataset.position || '';
                    break;
                case 'joining_date':
                    aVal = new Date(a.dataset.joiningDate) || new Date(0);
                    bVal = new Date(b.dataset.joiningDate) || new Date(0);
                    break;
                default:
                    return 0;
            }
            
            if (sortBy === 'joining_date') {
                return bVal - aVal; // Most recent first
            } else {
                return aVal.toString().localeCompare(bVal.toString());
            }
        });
        
        // Reorder DOM with animation
        this.elements.placementsList?.classList.add('loading');
        
        setTimeout(() => {
            cards.forEach(card => this.elements.placementsList?.appendChild(card));
            this.elements.placementsList?.classList.remove('loading');
        }, 150);
    }

    clearFilters() {
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        if (this.elements.clientFilter) this.elements.clientFilter.value = '';
        
        this.filterPlacements();
        this.showToast('Filters cleared', 'success');
    }

    handleDeletePlacement(button) {
        const placementId = button.dataset.placementId;
        const placementName = button.closest('.placement-card')?.querySelector('.placement-card__name')?.textContent;
        
        if (confirm(this.config.translations?.confirmDelete || 'Are you sure you want to delete this placement?')) {
            this.deletePlacement(placementId, placementName);
        }
    }

    async deletePlacement(placementId, placementName) {
        try {
            const response = await fetch(`/invoicing/placements/${placementId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove card with animation
                const card = document.querySelector(`[data-placement-id="${placementId}"]`)?.closest('.placement-card');
                if (card) {
                    card.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        card.remove();
                        this.updateStats();
                        this.showToast(data.message || `Placement "${placementName}" deleted successfully`, 'success');
                    }, 300);
                }
            } else {
                this.showToast(data.message || 'Error deleting placement', 'error');
            }
        } catch (error) {
            console.error('Error deleting placement:', error);
            this.showToast('Error deleting placement', 'error');
        }
    }

    updateStats() {
        const visibleCards = document.querySelectorAll('.placement-card:not([style*="display: none"])');
        const stats = {
            total: visibleCards.length,
            eligible: 0,
            pending: 0,
            invoiced: 0
        };
        
        visibleCards.forEach(card => {
            const status = card.dataset.status;
            if (status === 'eligible') {
                stats.eligible++;
            } else if (status === 'not-eligible') {
                stats.pending++;
            } else if (status === 'invoiced') {
                stats.invoiced++;
            }
        });
        
        // Update stat counters
        const totalElement = document.getElementById('totalCount');
        const eligibleElement = document.getElementById('eligibleCount');
        const pendingElement = document.getElementById('pendingCount');
        const invoicedElement = document.getElementById('invoicedCount');
        
        if (totalElement) totalElement.textContent = stats.total;
        if (eligibleElement) eligibleElement.textContent = stats.eligible;
        if (pendingElement) pendingElement.textContent = stats.pending;
        if (invoicedElement) invoicedElement.textContent = stats.invoiced;
    }

    updatePlacementCount(count = null) {
        if (!this.elements.placementCount) return;
        
        if (count === null) {
            count = document.querySelectorAll('.placement-card:not([style*="display: none"])').length;
        }
        
        const text = this.config.translations?.placements || 'Placements';
        this.elements.placementCount.textContent = `${count} ${text}`;
    }

    toggleNoResultsMessage(show) {
        if (this.elements.noResultsMessage) {
            this.elements.noResultsMessage.style.display = show ? 'block' : 'none';
        }
        
        if (this.elements.placementsList) {
            this.elements.placementsList.style.display = show ? 'none' : '';
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

    showToast(message, type = 'info') {
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
        document.querySelectorAll('[title]').forEach(element => {
            if (window.bootstrap?.Tooltip) {
                new bootstrap.Tooltip(element);
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PlacementListManager();
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
