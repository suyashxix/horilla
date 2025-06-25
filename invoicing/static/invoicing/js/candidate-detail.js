/**
 * Candidate Detail Management JavaScript
 */

class CandidateDetailManager {
    constructor() {
        this.candidateId = this.getCandidateIdFromUrl();
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeCharts();
        this.loadAdditionalData();
        console.log('Candidate Detail Manager initialized');
    }

    getCandidateIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const candidatesIndex = pathParts.indexOf('candidates');
        return candidatesIndex !== -1 ? pathParts[candidatesIndex + 1] : null;
    }

    bindEvents() {
        // Quick action buttons
        this.bindQuickActions();
        
        // Status change handling
        this.bindStatusChange();
        
        // Notes editing
        this.bindNotesEditing();
        
        // Print functionality
        this.bindPrintFunctionality();
    }

    bindQuickActions() {
        // Email button
        const emailBtn = document.querySelector('[href^="mailto:"]');
        emailBtn?.addEventListener('click', () => {
            this.trackAction('email_sent');
        });

        // Phone button
        const phoneBtn = document.querySelector('[href^="tel:"]');
        phoneBtn?.addEventListener('click', () => {
            this.trackAction('phone_call');
        });

        // LinkedIn button
        const linkedinBtn = document.querySelector('[href*="linkedin.com"]');
        linkedinBtn?.addEventListener('click', () => {
            this.trackAction('linkedin_viewed');
        });
    }

    bindStatusChange() {
        // Add status change dropdown if user has permissions
        const statusBadge = document.querySelector('.status-badge');
        if (statusBadge && this.hasEditPermission()) {
            statusBadge.style.cursor = 'pointer';
            statusBadge.addEventListener('click', () => {
                this.showStatusChangeModal();
            });
        }
    }

    bindNotesEditing() {
        const notesSection = document.querySelector('.oh-card:has(h5:contains("Internal Notes"))');
        if (notesSection && this.hasEditPermission()) {
            const editBtn = document.createElement('button');
            editBtn.className = 'oh-btn oh-btn--light oh-btn--sm';
            editBtn.innerHTML = '<i class="oh-icon-edit me-1"></i>Edit';
            editBtn.addEventListener('click', () => this.enableNotesEditing());
            
            const header = notesSection.querySelector('.oh-card__header');
            header?.appendChild(editBtn);
        }
    }

    bindPrintFunctionality() {
        // Add print button to header
        const headerActions = document.querySelector('.oh-titlebar__actions');
        if (headerActions) {
            const printBtn = document.createElement('button');
            printBtn.className = 'oh-btn oh-btn--light me-2';
            printBtn.innerHTML = '<i class="oh-icon-printer me-2"></i>Print Profile';
            printBtn.addEventListener('click', () => this.printProfile());
            
            headerActions.insertBefore(printBtn, headerActions.firstChild);
        }
    }

    showStatusChangeModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Change Candidate Status</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="oh-form__group">
                            <label class="oh-form__label">Select New Status</label>
                            <select class="oh-form__input" id="newStatus">
                                <option value="active">Active</option>
                                <option value="placed">Placed</option>
                                <option value="inactive">Inactive</option>
                                <option value="blacklisted">Blacklisted</option>
                            </select>
                        </div>
                        <div class="oh-form__group mt-3">
                            <label class="oh-form__label">Reason (Optional)</label>
                            <textarea class="oh-form__input" id="statusReason" rows="3" placeholder="Reason for status change..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="candidateDetailManager.updateStatus()">Update Status</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Remove modal from DOM when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    async updateStatus() {
        const newStatus = document.getElementById('newStatus').value;
        const reason = document.getElementById('statusReason').value;
        
        try {
            const response = await fetch(`/invoicing/candidates/${this.candidateId}/update-status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    status: newStatus,
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update status badge
                const statusBadge = document.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = `status-badge status-badge--${newStatus}`;
                    statusBadge.innerHTML = `<i class="oh-icon-${this.getStatusIcon(newStatus)} me-1"></i>${data.status_display}`;
                }
                
                this.showToast('Status updated successfully', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.querySelector('.modal'));
                modal?.hide();
            } else {
                this.showToast(data.message || 'Error updating status', 'error');
            }
        } catch (error) {
            console.error('Error updating status:', error);
            this.showToast('Error updating status', 'error');
        }
    }

    enableNotesEditing() {
        const notesContent = document.querySelector('.oh-card:has(h5:contains("Internal Notes")) .oh-card__body p');
        if (!notesContent) return;
        
        const currentText = notesContent.textContent;
        
        // Replace content with textarea
        notesContent.innerHTML = `
            <textarea class="oh-form__input" id="editNotes" rows="4">${currentText}</textarea>
            <div class="mt-3">
                <button class="oh-btn oh-btn--primary oh-btn--sm me-2" onclick="candidateDetailManager.saveNotes()">Save</button>
                <button class="oh-btn oh-btn--light oh-btn--sm" onclick="candidateDetailManager.cancelNotesEdit()">Cancel</button>
            </div>
        `;
        
        document.getElementById('editNotes').focus();
    }

    async saveNotes() {
        const newNotes = document.getElementById('editNotes').value;
        
        try {
            const response = await fetch(`/invoicing/candidates/${this.candidateId}/update-notes/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({ notes: newNotes })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update notes display
                const notesContent = document.querySelector('.oh-card:has(h5:contains("Internal Notes")) .oh-card__body');
                notesContent.innerHTML = `<p>${newNotes || 'No notes available'}</p>`;
                
                this.showToast('Notes updated successfully', 'success');
            } else {
                this.showToast(data.message || 'Error updating notes', 'error');
            }
        } catch (error) {
            console.error('Error updating notes:', error);
            this.showToast('Error updating notes', 'error');
        }
    }

    cancelNotesEdit() {
        // Reload the page to restore original content
        window.location.reload();
    }

    printProfile() {
        const printWindow = window.open('', '_blank');
        const candidateName = document.querySelector('.oh-title').textContent.replace('👤', '').trim();
        
        const printContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Candidate Profile - ${candidateName}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
                    .section { margin-bottom: 25px; }
                    .section h3 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
                    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                    .info-item { margin-bottom: 10px; }
                    .info-item label { font-weight: bold; color: #666; }
                    .skills { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
                    .skill { background: #f0f0f0; padding: 3px 8px; border-radius: 12px; font-size: 12px; }
                    @media print { body { margin: 0; } }
                </style>
            </head>
            <body>
                ${this.generatePrintContent()}
            </body>
            </html>
        `;
        
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.print();
    }

    generatePrintContent() {
        // Extract candidate information from the page
        const name = document.querySelector('.oh-title').textContent.replace('👤', '').trim();
        const status = document.querySelector('.status-badge').textContent.trim();
        
        // Get all info items
        const infoItems = document.querySelectorAll('.info-item');
        let personalInfo = '';
        let professionalInfo = '';
        
        infoItems.forEach((item, index) => {
            const label = item.querySelector('label')?.textContent || '';
            const value = item.querySelector('p')?.textContent || '';
            
            const infoHtml = `
                <div class="info-item">
                    <label>${label}</label>
                    <div>${value}</div>
                </div>
            `;
            
            if (index < 6) {
                personalInfo += infoHtml;
            } else {
                professionalInfo += infoHtml;
            }
        });
        
        return `
            <div class="header">
                <h1>${name}</h1>
                <p>Status: ${status}</p>
                <p>Generated on: ${new Date().toLocaleDateString()}</p>
            </div>
            
            <div class="section">
                <h3>Personal Information</h3>
                <div class="info-grid">
                    ${personalInfo}
                </div>
            </div>
            
            <div class="section">
                <h3>Professional Information</h3>
                <div class="info-grid">
                    ${professionalInfo}
                </div>
            </div>
        `;
    }

    initializeCharts() {
        // Initialize any charts or graphs for candidate statistics
        // This could include placement success rate, revenue generated, etc.
    }

    async loadAdditionalData() {
        // Load additional data that might not be in the initial page load
        // Such as recent activities, communication history, etc.
    }

    trackAction(action) {
        // Track user actions for analytics
        console.log(`Action tracked: ${action} for candidate ${this.candidateId}`);
        
        // You could send this to an analytics service
        // analytics.track(action, { candidateId: this.candidateId });
    }

    hasEditPermission() {
        // Check if user has permission to edit candidate
        // This would typically check user roles/permissions
        return true; // Simplified for now
    }

    getStatusIcon(status) {
        const icons = {
            'active': 'check-circle',
            'placed': 'user-check',
            'inactive': 'pause-circle',
            'blacklisted': 'x-circle'
        };
        return icons[status] || 'circle';
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
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
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.candidateDetailManager = new CandidateDetailManager();
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
    
    .status-badge:hover {
        opacity: 0.8;
        transform: scale(1.05);
        transition: all 0.2s ease;
    }
`;
document.head.appendChild(style);
