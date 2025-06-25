/**
 * Invoice List Management JavaScript
 * Handles filtering, sorting, and invoice actions
 */

class InvoiceListManager {
    constructor() {
        this.config = window.INVOICE_CONFIG || {};
        this.elements = {
            searchInput: document.getElementById('invoiceSearch'),
            statusFilter: document.getElementById('statusFilter'),
            typeFilter: document.getElementById('typeFilter'),
            dateFilter: document.getElementById('dateFilter'),
            clearFiltersBtn: document.getElementById('clearFilters'),
            clearSearchBtn: document.getElementById('clearSearchBtn'),
            invoiceRows: document.querySelectorAll('.invoice-row'),
            invoiceCount: document.getElementById('invoiceCount'),
            tableBody: document.getElementById('invoicesTableBody'),
            noResultsMessage: document.getElementById('noResultsMessage'),
            emptyState: document.getElementById('emptyState')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateStats();
        this.initializeTooltips();
        console.log('Invoice List Manager initialized');
    }

    bindEvents() {
        // Search and filter events
        this.elements.searchInput?.addEventListener('input', 
            this.debounce(() => this.filterInvoices(), 300)
        );
        
        this.elements.statusFilter?.addEventListener('change', () => this.filterInvoices());
        this.elements.typeFilter?.addEventListener('change', () => this.filterInvoices());
        this.elements.dateFilter?.addEventListener('change', () => this.filterInvoices());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.elements.clearSearchBtn?.addEventListener('click', () => this.clearFilters());

        // Table sorting
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', (e) => this.handleSort(e));
        });

        // FIXED: Invoice action buttons with proper event delegation
        document.addEventListener('click', (e) => {
            const button = e.target.closest('[data-action]');
            if (button) {
                e.preventDefault();
                const action = button.dataset.action;
                const invoiceId = button.dataset.invoiceId;
                const invoiceType = button.dataset.invoiceType;
                
                switch(action) {
                    case 'mark-paid':
                        this.handleMarkPaid(invoiceId, invoiceType);
                        break;
                    case 'send':
                        this.handleSendInvoice(invoiceId, invoiceType);
                        break;
                    case 'view':
                        this.handleViewInvoice(invoiceId, invoiceType);
                        break;
                }
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

    filterInvoices() {
        const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
        const statusValue = this.elements.statusFilter?.value || '';
        const typeValue = this.elements.typeFilter?.value || '';
        const dateValue = this.elements.dateFilter?.value || '';
        const today = new Date();
        
        let visibleCount = 0;
        
        this.elements.invoiceRows.forEach(row => {
            let show = true;
            
            // Search filter
            if (searchTerm) {
                const invoiceNumber = row.dataset.invoiceNumber || '';
                const client = row.dataset.client || '';
                const service = row.dataset.service || '';
                
                if (!invoiceNumber.includes(searchTerm) && 
                    !client.includes(searchTerm) && 
                    !service.includes(searchTerm)) {
                    show = false;
                }
            }
            
            // Status filter
            if (statusValue && row.dataset.status !== statusValue) {
                show = false;
            }
            
            // Type filter
            if (typeValue && row.dataset.type !== typeValue) {
                show = false;
            }
            
            // Date filter
            if (dateValue) {
                const issueDate = new Date(row.dataset.issueDate);
                const dueDate = new Date(row.dataset.dueDate);
                
                switch(dateValue) {
                    case 'today':
                        if (issueDate.toDateString() !== today.toDateString()) {
                            show = false;
                        }
                        break;
                    case 'week':
                        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (issueDate < weekAgo) {
                            show = false;
                        }
                        break;
                    case 'month':
                        const monthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
                        if (issueDate < monthAgo) {
                            show = false;
                        }
                        break;
                    case 'overdue':
                        if (dueDate >= today || row.dataset.status === 'paid') {
                            show = false;
                        }
                        break;
                }
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
        
        // Update count and visibility
        this.updateInvoiceCount(visibleCount);
        this.toggleNoResultsMessage(visibleCount === 0);
        this.updateStats();
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
        
        this.sortInvoicesByColumn(sortBy, isAscending);
    }

    sortInvoicesByColumn(sortBy, ascending = true) {
        const rows = Array.from(this.elements.invoiceRows);
        
        rows.sort((a, b) => {
            let aVal = a.dataset[sortBy] || '';
            let bVal = b.dataset[sortBy] || '';
            
            // Handle different data types
            if (sortBy === 'amount') {
                aVal = parseFloat(aVal) || 0;
                bVal = parseFloat(bVal) || 0;
            } else if (sortBy === 'due_date' || sortBy === 'issue_date') {
                aVal = new Date(aVal) || new Date(0);
                bVal = new Date(bVal) || new Date(0);
            }
            
            let result;
            if (aVal < bVal) result = -1;
            else if (aVal > bVal) result = 1;
            else result = 0;
            
            return ascending ? result : -result;
        });
        
        // Reorder DOM with animation
        this.elements.tableBody?.classList.add('loading');
        
        setTimeout(() => {
            rows.forEach(row => this.elements.tableBody?.appendChild(row));
            this.elements.tableBody?.classList.remove('loading');
        }, 150);
    }

    clearFilters() {
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        if (this.elements.typeFilter) this.elements.typeFilter.value = '';
        if (this.elements.dateFilter) this.elements.dateFilter.value = '';
        
        this.filterInvoices();
        this.showToast('Filters cleared', 'success');
    }

    handleMarkPaid(invoiceId, invoiceType) {
        this.markInvoiceAsPaid(invoiceId, invoiceType);
    }

    handleSendInvoice(invoiceId, invoiceType) {
        this.sendInvoice(invoiceId, invoiceType);
    }

    handleViewInvoice(invoiceId, invoiceType) {
        // Redirect to invoice detail page
        if (invoiceType === 'recruitment') {
            window.location.href = `/invoicing/invoices/${invoiceId}/`;
        } else {
            window.location.href = `/invoicing/general-invoices/${invoiceId}/`;
        }
    }

    async markInvoiceAsPaid(invoiceId, type) {
        if (!confirm(this.config.translations?.confirmMarkPaid || 'Are you sure you want to mark this invoice as paid?')) {
            return;
        }

        try {
            const url = type === 'recruitment' 
                ? `/invoicing/invoices/${invoiceId}/mark-paid/`
                : `/invoicing/general-invoices/${invoiceId}/mark-paid/`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });
            
            if (response.ok) {
                // Update the row status
                const row = document.querySelector(`[data-invoice-id="${invoiceId}"]`)?.closest('tr');
                if (row) {
                    row.dataset.status = 'paid';
                    const statusBadge = row.querySelector('.badge:last-of-type');
                    if (statusBadge) {
                        statusBadge.className = 'badge bg-success';
                        statusBadge.textContent = 'Paid';
                    }
                    
                    // Remove mark-paid button
                    const markPaidBtn = row.querySelector('[data-action="mark-paid"]');
                    if (markPaidBtn) {
                        markPaidBtn.remove();
                    }
                }
                
                this.updateStats();
                this.showToast('Invoice marked as paid successfully', 'success');
            } else {
                throw new Error('Failed to mark invoice as paid');
            }
        } catch (error) {
            console.error('Error marking invoice as paid:', error);
            this.showToast(this.config.translations?.errorMarkPaid || 'Error marking invoice as paid', 'error');
        }
    }

    async sendInvoice(invoiceId, type) {
        if (!confirm(this.config.translations?.confirmSend || 'Are you sure you want to send this invoice?')) {
            return;
        }

        try {
            const url = type === 'recruitment' 
                ? `/invoicing/invoices/${invoiceId}/send-email/`
                : `/invoicing/general-invoices/${invoiceId}/send-email/`;
            
            // For now, redirect to the send email page instead of AJAX
            window.location.href = url;
            
        } catch (error) {
            console.error('Error sending invoice:', error);
            this.showToast(this.config.translations?.errorSend || 'Error sending invoice', 'error');
        }
    }

    updateStats() {
        const visibleRows = document.querySelectorAll('.invoice-row:not([style*="display: none"])');
        const stats = {
            recruitment: 0,
            general: 0,
            draft: 0,
            sent: 0,
            paid: 0,
            overdue: 0
        };
        
        visibleRows.forEach(row => {
            const status = row.dataset.status;
            const type = row.dataset.type;
            
            if (stats.hasOwnProperty(status)) {
                stats[status]++;
            }
            if (stats.hasOwnProperty(type)) {
                stats[type]++;
            }
        });
        
        // Update stat counters
        Object.keys(stats).forEach(key => {
            const element = document.getElementById(key + 'Count');
            if (element) {
                element.textContent = stats[key];
            }
        });
    }

    updateInvoiceCount(count = null) {
        if (!this.elements.invoiceCount) return;
        
        if (count === null) {
            count = document.querySelectorAll('.invoice-row:not([style*="display: none"])').length;
        }
        
        const text = this.config.translations?.invoices || 'Total';
        this.elements.invoiceCount.textContent = `${count} ${text}`;
    }

    toggleNoResultsMessage(show) {
        if (this.elements.noResultsMessage) {
            this.elements.noResultsMessage.style.display = show ? 'block' : 'none';
        }
        
        if (this.elements.tableBody) {
            this.elements.tableBody.style.display = show ? 'none' : '';
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
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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
    new InvoiceListManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
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
