/**
 * Invoice Detail Management JavaScript
 */

class InvoiceDetailManager {
    constructor() {
        this.invoiceId = this.getInvoiceIdFromUrl();
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeModals();
        console.log('Invoice Detail Manager initialized');
    }

    getInvoiceIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const invoicesIndex = pathParts.indexOf('invoices');
        return invoicesIndex !== -1 ? pathParts[invoicesIndex + 1] : null;
    }

    bindEvents() {
        // Dropdown functionality
        this.bindDropdownEvents();
        
        // Modal events
        this.bindModalEvents();
        
        // Form submissions
        this.bindFormEvents();
    }

    bindDropdownEvents() {
        document.querySelectorAll('.oh-dropdown__toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => this.toggleDropdown(e));
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => this.closeDropdowns(e));
    }

    bindModalEvents() {
        // Email modal events
        const emailModal = document.getElementById('emailModal');
        if (emailModal) {
            emailModal.addEventListener('show.bs.modal', () => {
                this.prepareEmailModal();
            });
        }

        // PDF upload modal events
        const uploadModal = document.getElementById('uploadPdfModal');
        if (uploadModal) {
            uploadModal.addEventListener('show.bs.modal', () => {
                this.preparePdfUploadModal();
            });
        }
    }

    bindFormEvents() {
        // Email form submission
        const emailForm = document.getElementById('emailForm');
        if (emailForm) {
            emailForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendEmail();
            });
        }

        // PDF upload form
        const pdfForm = document.getElementById('pdfUploadForm');
        if (pdfForm) {
            pdfForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.uploadPdf();
            });
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

    prepareEmailModal() {
        // Focus on subject field when modal opens
        setTimeout(() => {
            const subjectField = document.getElementById('email_subject');
            if (subjectField) {
                subjectField.focus();
            }
        }, 150);
    }

    preparePdfUploadModal() {
        // Reset file input when modal opens
        const fileInput = document.getElementById('pdf_file');
        if (fileInput) {
            fileInput.value = '';
        }
    }

    async markAsPaid() {
        if (!confirm('Are you sure you want to mark this invoice as paid?')) {
            return;
        }

        try {
            const response = await fetch(`/invoicing/invoices/${this.invoiceId}/mark-paid/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=mark_paid'
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Invoice marked as paid successfully!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                this.showToast('Error: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error marking invoice as paid', 'error');
        }
    }

    async sendEmail() {
        const form = document.getElementById('emailForm');
        const formData = new FormData(form);
        
        // Show loading state
        const sendBtn = document.querySelector('#emailModal .btn-primary');
        const originalText = sendBtn.textContent;
        sendBtn.textContent = 'Sending...';
        sendBtn.disabled = true;
        sendBtn.classList.add('btn-loading');
        
        try {
            const response = await fetch(`/invoicing/invoices/${this.invoiceId}/send-email/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Invoice sent successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('emailModal')).hide();
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                this.showToast('Error: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error sending invoice', 'error');
        } finally {
            // Reset button state
            sendBtn.textContent = originalText;
            sendBtn.disabled = false;
            sendBtn.classList.remove('btn-loading');
        }
    }

    async uploadPdf() {
        const form = document.getElementById('pdfUploadForm');
        const formData = new FormData(form);
        
        // Validate file
        const fileInput = document.getElementById('pdf_file');
        if (!fileInput.files[0]) {
            this.showToast('Please select a PDF file', 'error');
            return;
        }

        // Show loading state
        const uploadBtn = document.querySelector('#uploadPdfModal .btn-primary');
        const originalText = uploadBtn.textContent;
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        uploadBtn.classList.add('btn-loading');
        
        try {
            const response = await fetch(`/invoicing/invoices/${this.invoiceId}/upload-pdf/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('PDF uploaded successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('uploadPdfModal')).hide();
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                this.showToast('Error: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error uploading PDF', 'error');
        } finally {
            // Reset button state
            uploadBtn.textContent = originalText;
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('btn-loading');
        }
    }

    async generatePdf() {
        try {
            // Show loading state
            const generateBtn = event.target;
            const originalText = generateBtn.textContent;
            generateBtn.textContent = 'Generating...';
            generateBtn.disabled = true;
            generateBtn.classList.add('btn-loading');

            const response = await fetch(`/invoicing/invoices/${this.invoiceId}/download-pdf/`, {
                method: 'GET',
            });

            if (response.ok) {
                // Create download link
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Invoice_${this.invoiceId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showToast('PDF generated and downloaded successfully!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                this.showToast('Error generating PDF', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error generating PDF', 'error');
        } finally {
            // Reset button state
            if (event.target) {
                event.target.textContent = originalText;
                event.target.disabled = false;
                event.target.classList.remove('btn-loading');
            }
        }
    }

    initializeModals() {
        // Initialize Bootstrap modals if available
        if (typeof bootstrap !== 'undefined') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                new bootstrap.Modal(modal);
            });
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} toast-message`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            z-index: 9999;
            border-radius: 6px;
            animation: slideIn 0.3s ease;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Global functions for onclick events
function markAsPaid(invoiceId) {
    if (window.invoiceDetailManager) {
        window.invoiceDetailManager.markAsPaid();
    }
}

function sendEmail(invoiceId) {
    if (window.invoiceDetailManager) {
        window.invoiceDetailManager.sendEmail();
    }
}

function uploadPdf(invoiceId) {
    if (window.invoiceDetailManager) {
        window.invoiceDetailManager.uploadPdf();
    }
}

function generatePdf(invoiceId) {
    if (window.invoiceDetailManager) {
        window.invoiceDetailManager.generatePdf();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.invoiceDetailManager = new InvoiceDetailManager();
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
`;
document.head.appendChild(style);
