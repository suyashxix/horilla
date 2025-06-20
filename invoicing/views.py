from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q
from .models import Client, Placement, Invoice, InvoiceNotification
from .forms import ClientForm, PlacementForm, InvoiceForm, EmailForm

@login_required
def dashboard(request):
    """Main dashboard showing notifications and recent invoices"""
    # Get notifications for current user
    notifications = InvoiceNotification.objects.filter(
        notified_user=request.user,
        is_read=False
    )[:10]
    
    # Get recent invoices
    recent_invoices = Invoice.objects.all().order_by('-created_at')[:10]
    
    # Get placements eligible for invoicing
    eligible_placements = Placement.objects.filter(
        invoice__isnull=True,  # No invoice created yet
        is_active=True
    )
    
    eligible_count = sum(1 for p in eligible_placements if p.is_invoice_eligible)
    
    context = {
        'notifications': notifications,
        'recent_invoices': recent_invoices,
        'eligible_count': eligible_count,
        'total_placements': eligible_placements.count(),
    }
    return render(request, 'invoicing/dashboard.html', context)

@login_required
def client_list(request):
    """List all clients"""
    clients = Client.objects.filter(is_active=True).order_by('name')
    return render(request, 'invoicing/client_list.html', {'clients': clients})

@login_required
def client_create(request):
    """Create new client"""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client created successfully!')
            return redirect('invoicing:client_list')
    else:
        form = ClientForm()
    return render(request, 'invoicing/client_form.html', {'form': form, 'title': 'Create Client'})

@login_required
def placement_list(request):
    """List all placements with invoice eligibility status"""
    placements = Placement.objects.filter(is_active=True).order_by('-created_at')
    
    # Add eligibility info to each placement
    placement_data = []
    for placement in placements:
        placement_data.append({
            'placement': placement,
            'is_eligible': placement.is_invoice_eligible,
            'days_until_eligible': placement.days_until_eligible,
            'has_invoice': hasattr(placement, 'invoice')
        })
    
    return render(request, 'invoicing/placement_list.html', {'placement_data': placement_data})

@login_required
def placement_create(request):
    """Create new placement"""
    if request.method == 'POST':
        form = PlacementForm(request.POST, user=request.user)
        if form.is_valid():
            placement = form.save(commit=False)
            placement.created_by = request.user
            placement.save()
            messages.success(request, 'Placement created successfully!')
            return redirect('invoicing:placement_list')
    else:
        form = PlacementForm(user=request.user)
    return render(request, 'invoicing/placement_form.html', {'form': form, 'title': 'Create Placement'})

@login_required
def invoice_create(request, placement_id):
    """Create invoice for a placement"""
    placement = get_object_or_404(Placement, id=placement_id)
    
    # Check if placement is eligible
    if not placement.is_invoice_eligible:
        messages.error(request, f"Invoice cannot be created yet. Eligible from {placement.invoice_eligible_date}")
        return redirect('invoicing:placement_list')
    
    # Check if invoice already exists
    if hasattr(placement, 'invoice'):
        messages.info(request, "Invoice already exists for this placement")
        return redirect('invoicing:invoice_detail', invoice_id=placement.invoice.id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.placement = placement
            if not invoice.amount:
                invoice.amount = placement.placement_fee
            invoice.save()
            
            # Mark notification as read
            InvoiceNotification.objects.filter(placement=placement).update(is_read=True)
            
            messages.success(request, "Invoice created successfully!")
            return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm(initial={'amount': placement.placement_fee})
    
    context = {
        'form': form,
        'placement': placement,
        'title': f'Create Invoice for {placement.candidate}'
    }
    return render(request, 'invoicing/invoice_form.html', context)

@login_required
def invoice_detail(request, invoice_id):
    """Show invoice details with email sending capability"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Prepare default email content
    default_subject = f"Invoice {invoice.invoice_number} - Recruitment Services"
    default_body = f"""Dear {invoice.placement.client.contact_person},

I hope this email finds you well.

Please find attached the invoice for the successful placement of {invoice.placement.candidate} for the position of {invoice.placement.position} at {invoice.placement.client.name}.

As per our agreement, the notice period of {invoice.placement.notice_period_days} days has been completed, and the placement is now confirmed.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Amount: ₹{invoice.amount:,.2f}
- Tax ({invoice.tax_rate}%): ₹{(invoice.amount * invoice.tax_rate / 100):,.2f}
- Total Amount: ₹{invoice.total_amount:,.2f}
- Due Date: {invoice.due_date.strftime('%B %d, %Y')}

Please process the payment at your earliest convenience. If you have any questions or need additional information, please don't hesitate to contact me.

Thank you for your business.

Best regards,
{request.user.get_full_name() or request.user.username}"""

    context = {
        'invoice': invoice,
        'default_subject': default_subject,
        'default_body': default_body,
    }
    return render(request, 'invoicing/invoice_detail.html', context)

@login_required
def send_invoice_email(request, invoice_id):
    """Send invoice via email"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            
            try:
                # Send email
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[invoice.placement.client.email],
                )
                
                # Attach PDF if exists
                if invoice.pdf_file:
                    email.attach_file(invoice.pdf_file.path)
                
                email.send()
                
                # Update invoice
                invoice.status = 'sent'
                invoice.email_subject = subject
                invoice.email_body = body
                invoice.sent_at = timezone.now()
                invoice.sent_by = request.user
                invoice.save()
                
                messages.success(request, "Invoice sent successfully!")
                return JsonResponse({'success': True})
                
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def invoice_list(request):
    """List all invoices with filtering"""
    invoices = Invoice.objects.all().order_by('-created_at')
    
    # Add search functionality
    search = request.GET.get('search')
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(placement__candidate__first_name__icontains=search) |
            Q(placement__client__name__icontains=search)
        )
    
    # Add status filtering
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    context = {
        'invoices': invoices,
        'status_choices': Invoice.STATUS_CHOICES,
        'current_search': search,
        'current_status': status,
    }
    return render(request, 'invoicing/invoice_list.html', context)
