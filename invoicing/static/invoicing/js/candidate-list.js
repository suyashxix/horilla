/**
 * Candidate List Management JavaScript
 */

class CandidateListManager {
    constructor() {
        this.config = window.CANDIDATE_CONFIG || {};
        this.elements = {
            searchInput: document.getElementById('candidateSearch'),
            statusFilter: document.getElementById('statusFilter'),
            experienceFilter: document.getElementById('experienceFilter'),
            sortFilter: document.getElementById('sortFilter'),
            clearFiltersBtn: document.getElementById('clearFilters'),
            clearSearchBtn: document.getElementById('clearSearchBtn'),
            candidateCards: document.querySelectorAll('.candidate-card'),
            candidateCount: document.getElementById('candidateCount'),
            candidatesList: document.getElementById('candidatesList'),
            noResultsMessage: document.getElementById('noResultsMessage'),
            emptyState: document.getElementById('emptyState')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateStats();
        this.initializeTooltips();
        console.log('Candidate List Manager initialized');
    }

    bindEvents() {
        // Search and filter events
        this.elements.searchInput?.addEventListener('input', 
            this.debounce(() => this.filterCandidates(), 300)
        );
        
        this.elements.statusFilter?.addEventListener('change', () => this.filterCandidates());
        this.elements.experienceFilter?.addEventListener('change', () => this.filterCandidates());
        this.elements.sortFilter?.addEventListener('change', () => this.sortCandidates());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.elements.clearSearchBtn?.addEventListener('click', () => this.clearFilters());

        // Candidate action buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="delete"]')) {
                e.preventDefault();
                this.handleDeleteCandidate(e.target.closest('[data-action="delete"]'));
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

    filterCandidates() {
        const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
        const statusValue = this.elements.statusFilter?.value || '';
        const experienceValue = this.elements.experienceFilter?.value || '';
        
        let visibleCount = 0;
        
        this.elements.candidateCards.forEach(card => {
            let show = true;
            
            // Search filter
            if (searchTerm) {
                const name = card.dataset.name || '';
                const email = card.dataset.email || '';
                const skills = card.dataset.skills || '';
                
                if (!name.includes(searchTerm) && 
                    !email.includes(searchTerm) && 
                    !skills.includes(searchTerm)) {
                    show = false;
                }
            }
            
            // Status filter
            if (statusValue && card.dataset.status !== statusValue) {
                show = false;
            }
            
            // Experience filter
            if (experienceValue && card.dataset.experience !== experienceValue) {
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
        this.updateCandidateCount(visibleCount);
        this.toggleNoResultsMessage(visibleCount === 0);
        this.updateStats();
    }

    sortCandidates() {
        const sortBy = this.elements.sortFilter?.value || 'name';
        const cards = Array.from(this.elements.candidateCards);
        
        cards.sort((a, b) => {
            let aVal = '';
            let bVal = '';
            
            switch(sortBy) {
                case 'name':
                    aVal = a.dataset.name || '';
                    bVal = b.dataset.name || '';
                    break;
                case 'experience':
                    aVal = parseInt(a.dataset.experience) || 0;
                    bVal = parseInt(b.dataset.experience) || 0;
                    break;
                case 'salary':
                    aVal = parseFloat(a.dataset.salary) || 0;
                    bVal = parseFloat(b.dataset.salary) || 0;
                    break;
                case 'created':
                    aVal = new Date(a.dataset.created) || new Date(0);
                    bVal = new Date(b.dataset.created) || new Date(0);
                    break;
                default:
                    return 0;
            }
            
            if (sortBy === 'experience' || sortBy === 'salary') {
                return bVal - aVal; // Descending for numbers
            } else if (sortBy === 'created') {
                return bVal - aVal; // Most recent first
            } else {
                return aVal.toString().localeCompare(bVal.toString());
            }
        });
        
        // Reorder DOM with animation
        this.elements.candidatesList?.classList.add('loading');
        
        setTimeout(() => {
            cards.forEach(card => this.elements.candidatesList?.appendChild(card));
            this.elements.candidatesList?.classList.remove('loading');
        }, 150);
    }

    clearFilters() {
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        if (this.elements.experienceFilter) this.elements.experienceFilter.value = '';
        
        this.filterCandidates();
        this.showToast('Filters cleared', 'success');
    }

    handleDeleteCandidate(button) {
        const candidateId = button.dataset.candidateId;
        const candidateName = button.closest('.candidate-card')?.querySelector('.candidate-card__name')?.textContent;
        
        if (confirm(this.config.translations?.confirmDelete || 'Are you sure you want to delete this candidate?')) {
            this.deleteCandidate(candidateId, candidateName);
        }
    }

    async deleteCandidate(candidateId, candidateName) {
        try {
            const response = await fetch(`/invoicing/candidates/${candidateId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove card with animation
                const card = document.querySelector(`[data-candidate-id="${candidateId}"]`)?.closest('.candidate-card');
                if (card) {
                    card.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        card.remove();
                        this.updateStats();
                        this.showToast(data.message || `Candidate "${candidateName}" deleted successfully`, 'success');
                    }, 300);
                }
            } else {
                this.showToast(data.message || 'Error deleting candidate', 'error');
            }
        } catch (error) {
            console.error('Error deleting candidate:', error);
            this.showToast('Error deleting candidate', 'error');
        }
    }

    updateStats() {
        const visibleCards = document.querySelectorAll('.candidate-card:not([style*="display: none"])');
        const stats = {
            total: visibleCards.length,
            active: 0,
            placed: 0,
            inactive: 0
        };
        
        visibleCards.forEach(card => {
            const status = card.dataset.status;
            if (status === 'active') {
                stats.active++;
            } else if (status === 'placed') {
                stats.placed++;
            } else if (status === 'inactive') {
                stats.inactive++;
            }
        });
        
        // Update stat counters
        const totalElement = document.getElementById('totalCount');
        const activeElement = document.getElementById('activeCount');
        const placedElement = document.getElementById('placedCount');
        const inactiveElement = document.getElementById('inactiveCount');
        
        if (totalElement) totalElement.textContent = stats.total;
        if (activeElement) activeElement.textContent = stats.active;
        if (placedElement) placedElement.textContent = stats.placed;
        if (inactiveElement) inactiveElement.textContent = stats.inactive;
    }

    updateCandidateCount(count = null) {
        if (!this.elements.candidateCount) return;
        
        if (count === null) {
            count = document.querySelectorAll('.candidate-card:not([style*="display: none"])').length;
        }
        
        const text = this.config.translations?.candidates || 'Candidates';
        this.elements.candidateCount.textContent = `${count} ${text}`;
    }

    toggleNoResultsMessage(show) {
        if (this.elements.noResultsMessage) {
            this.elements.noResultsMessage.style.display = show ? 'block' : 'none';
        }
        
        if (this.elements.candidatesList) {
            this.elements.candidatesList.style.display = show ? 'none' : '';
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
    new CandidateListManager();
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
    
    .filtered-out {
        opacity: 0.5;
        transform: scale(0.98);
        transition: all 0.2s ease;
    }
`;
document.head.appendChild(style);
/**
 * Candidate List Management JavaScript
 */

class CandidateListManager {
    constructor() {
        this.config = window.CANDIDATE_CONFIG || {};
        this.elements = {
            searchInput: document.getElementById('candidateSearch'),
            statusFilter: document.getElementById('statusFilter'),
            experienceFilter: document.getElementById('experienceFilter'),
            sortFilter: document.getElementById('sortFilter'),
            clearFiltersBtn: document.getElementById('clearFilters'),
            clearSearchBtn: document.getElementById('clearSearchBtn'),
            candidateCards: document.querySelectorAll('.candidate-card'),
            candidateCount: document.getElementById('candidateCount'),
            candidatesList: document.getElementById('candidatesList'),
            noResultsMessage: document.getElementById('noResultsMessage'),
            emptyState: document.getElementById('emptyState')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateStats();
        this.initializeTooltips();
        console.log('Candidate List Manager initialized');
    }

    bindEvents() {
        // Search and filter events
        this.elements.searchInput?.addEventListener('input', 
            this.debounce(() => this.filterCandidates(), 300)
        );
        
        this.elements.statusFilter?.addEventListener('change', () => this.filterCandidates());
        this.elements.experienceFilter?.addEventListener('change', () => this.filterCandidates());
        this.elements.sortFilter?.addEventListener('change', () => this.sortCandidates());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.elements.clearSearchBtn?.addEventListener('click', () => this.clearFilters());

        // Candidate action buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="delete"]')) {
                e.preventDefault();
                this.handleDeleteCandidate(e.target.closest('[data-action="delete"]'));
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

    filterCandidates() {
        const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
        const statusValue = this.elements.statusFilter?.value || '';
        const experienceValue = this.elements.experienceFilter?.value || '';
        
        let visibleCount = 0;
        
        this.elements.candidateCards.forEach(card => {
            let show = true;
            
            // Search filter
            if (searchTerm) {
                const name = card.dataset.name || '';
                const email = card.dataset.email || '';
                const skills = card.dataset.skills || '';
                
                if (!name.includes(searchTerm) && 
                    !email.includes(searchTerm) && 
                    !skills.includes(searchTerm)) {
                    show = false;
                }
            }
            
            // Status filter
            if (statusValue && card.dataset.status !== statusValue) {
                show = false;
            }
            
            // Experience filter
            if (experienceValue && card.dataset.experience !== experienceValue) {
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
        this.updateCandidateCount(visibleCount);
        this.toggleNoResultsMessage(visibleCount === 0);
        this.updateStats();
    }

    sortCandidates() {
        const sortBy = this.elements.sortFilter?.value || 'name';
        const cards = Array.from(this.elements.candidateCards);
        
        cards.sort((a, b) => {
            let aVal = '';
            let bVal = '';
            
            switch(sortBy) {
                case 'name':
                    aVal = a.dataset.name || '';
                    bVal = b.dataset.name || '';
                    break;
                case 'experience':
                    aVal = parseInt(a.dataset.experience) || 0;
                    bVal = parseInt(b.dataset.experience) || 0;
                    break;
                case 'salary':
                    aVal = parseFloat(a.dataset.salary) || 0;
                    bVal = parseFloat(b.dataset.salary) || 0;
                    break;
                case 'created':
                    aVal = new Date(a.dataset.created) || new Date(0);
                    bVal = new Date(b.dataset.created) || new Date(0);
                    break;
                default:
                    return 0;
            }
            
            if (sortBy === 'experience' || sortBy === 'salary') {
                return bVal - aVal; // Descending for numbers
            } else if (sortBy === 'created') {
                return bVal - aVal; // Most recent first
            } else {
                return aVal.toString().localeCompare(bVal.toString());
            }
        });
        
        // Reorder DOM with animation
        this.elements.candidatesList?.classList.add('loading');
        
        setTimeout(() => {
            cards.forEach(card => this.elements.candidatesList?.appendChild(card));
            this.elements.candidatesList?.classList.remove('loading');
        }, 150);
    }

    clearFilters() {
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        if (this.elements.experienceFilter) this.elements.experienceFilter.value = '';
        
        this.filterCandidates();
        this.showToast('Filters cleared', 'success');
    }

    handleDeleteCandidate(button) {
        const candidateId = button.dataset.candidateId;
        const candidateName = button.closest('.candidate-card')?.querySelector('.candidate-card__name')?.textContent;
        
        if (confirm(this.config.translations?.confirmDelete || 'Are you sure you want to delete this candidate?')) {
            this.deleteCandidate(candidateId, candidateName);
        }
    }

    async deleteCandidate(candidateId, candidateName) {
        try {
            const response = await fetch(`/invoicing/candidates/${candidateId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove card with animation
                const card = document.querySelector(`[data-candidate-id="${candidateId}"]`)?.closest('.candidate-card');
                if (card) {
                    card.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        card.remove();
                        this.updateStats();
                        this.showToast(data.message || `Candidate "${candidateName}" deleted successfully`, 'success');
                    }, 300);
                }
            } else {
                this.showToast(data.message || 'Error deleting candidate', 'error');
            }
        } catch (error) {
            console.error('Error deleting candidate:', error);
            this.showToast('Error deleting candidate', 'error');
        }
    }

    updateStats() {
        const visibleCards = document.querySelectorAll('.candidate-card:not([style*="display: none"])');
        const stats = {
            total: visibleCards.length,
            active: 0,
            placed: 0,
            inactive: 0
        };
        
        visibleCards.forEach(card => {
            const status = card.dataset.status;
            if (status === 'active') {
                stats.active++;
            } else if (status === 'placed') {
                stats.placed++;
            } else if (status === 'inactive') {
                stats.inactive++;
            }
        });
        
        // Update stat counters
        const totalElement = document.getElementById('totalCount');
        const activeElement = document.getElementById('activeCount');
        const placedElement = document.getElementById('placedCount');
        const inactiveElement = document.getElementById('inactiveCount');
        
        if (totalElement) totalElement.textContent = stats.total;
        if (activeElement) activeElement.textContent = stats.active;
        if (placedElement) placedElement.textContent = stats.placed;
        if (inactiveElement) inactiveElement.textContent = stats.inactive;
    }

    updateCandidateCount(count = null) {
        if (!this.elements.candidateCount) return;
        
        if (count === null) {
            count = document.querySelectorAll('.candidate-card:not([style*="display: none"])').length;
        }
        
        const text = this.config.translations?.candidates || 'Candidates';
        this.elements.candidateCount.textContent = `${count} ${text}`;
    }

    toggleNoResultsMessage(show) {
        if (this.elements.noResultsMessage) {
            this.elements.noResultsMessage.style.display = show ? 'block' : 'none';
        }
        
        if (this.elements.candidatesList) {
            this.elements.candidatesList.style.display = show ? 'none' : '';
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
    new CandidateListManager();
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
    
    .filtered-out {
        opacity: 0.5;
        transform: scale(0.98);
        transition: all 0.2s ease;
    }
`;
document.head.appendChild(style);
