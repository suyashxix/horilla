// Invoicing Module JavaScript

$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Auto-refresh notifications every 5 minutes
    setInterval(function() {
        refreshNotifications();
    }, 300000);
    
    // Email form submission
    $('#emailForm').on('submit', function(e) {
        e.preventDefault();
        sendInvoiceEmail(this);
    });
    
    // Status filter change
    $('#statusFilter').on('change', function() {
        filterInvoices();
    });
    
    // Search functionality
    $('#invoiceSearch').on('keyup', function() {
        searchInvoices();
    });
});

// Refresh notifications
function refreshNotifications() {
    $.get('/invoicing/api/notifications/', function(data) {
        updateNotificationBadge(data.count);
    });
}

// Send invoice email
function sendInvoiceEmail(form) {
    const formData = new FormData(form);
    const invoiceId = $(form).data('invoice-id');
    
    // Show loading state
    const submitBtn = $(form).find('button[type="submit"]');
    const originalText = submitBtn.text();
    submitBtn.text('Sending...').prop('disabled', true);
    
    fetch(`/invoicing/invoices/${invoiceId}/send/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Invoice sent successfully!', 'success');
            location.reload();
        } else {
            showAlert('Error: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        showAlert('Network error occurred', 'danger');
    })
    .finally(() => {
        submitBtn.text(originalText).prop('disabled', false);
    });
}

// Show alert message
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('#alerts-container').html(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        $('.alert').fadeOut();
    }, 5000);
}

// Filter invoices
function filterInvoices() {
    const status = $('#statusFilter').val();
    const search = $('#invoiceSearch').val();
    
    let url = new URL(window.location);
    if (status) {
        url.searchParams.set('status', status);
    } else {
        url.searchParams.delete('status');
    }
    
    if (search) {
        url.searchParams.set('search', search);
    } else {
        url.searchParams.delete('search');
    }
    
    window.location = url;
}

// Search invoices
function searchInvoices() {
    const search = $('#invoiceSearch').val();
    
    // Debounce search
    clearTimeout(window.searchTimeout);
    window.searchTimeout = setTimeout(() => {
        filterInvoices();
    }, 500);
}

// Update notification badge
function updateNotificationBadge(count) {
    const badge = $('.notification-badge');
    if (count > 0) {
        badge.text(count).show();
    } else {
        badge.hide();
    }
}

// Copy invoice number to clipboard
function copyInvoiceNumber(invoiceNumber) {
    navigator.clipboard.writeText(invoiceNumber).then(() => {
        showAlert('Invoice number copied to clipboard!', 'info');
    });
}

// Print invoice
function printInvoice(invoiceId) {
    window.open(`/invoicing/invoices/${invoiceId}/pdf/`, '_blank');
}

// Download invoice
function downloadInvoice(invoiceId) {
    const link = document.createElement('a');
    link.href = `/invoicing/invoices/${invoiceId}/pdf/`;
    link.download = `invoice_${invoiceId}.pdf`;
    link.click();
}
