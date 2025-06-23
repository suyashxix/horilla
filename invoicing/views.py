from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q
from .models import Client, GeneralInvoice, Placement, Invoice, InvoiceNotification, InvoiceHistory
from .forms import ClientForm, GeneralInvoiceForm, PlacementForm, InvoiceForm, EmailForm
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
import json

from django.core.mail import EmailMessage
from django.conf import settings
import os

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
        'breadcrumb_list': [
            {'name': 'Horilla', 'url': '/'},
            {'name': 'Invoicing', 'url': '/invoicing/dashboard/'},
            {'name': 'Dashboard', 'url': ''}
        ]
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
            'days_until_eligible': placement.days_until_eligible_invoice,
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
    
    # Handle POST requests for actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_paid':
            return mark_invoice_paid(request, invoice_id)
        elif action == 'send_email':
            return send_invoice_email(request, invoice_id)
    
    # Calculate tax amount in the view
    tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
    
    # Fix: Handle None due_date
    due_date_str = invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'
    
    # Prepare default email content
    default_subject = f"Invoice {invoice.invoice_number} - Recruitment Services"
    default_body = f"""Dear {invoice.placement.client.contact_person},

I hope this email finds you well.

Please find attached the invoice for the successful placement of {invoice.placement.candidate.name} for the position of {invoice.placement.position} at {invoice.placement.client.name}.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Amount: ₹{invoice.amount:,.2f}
- Tax ({invoice.tax_rate}%): ₹{tax_amount:,.2f}
- Total Amount: ₹{invoice.total_amount:,.2f}
- Due Date: {due_date_str}

Please process the payment at your earliest convenience.

Best regards,
{request.user.get_full_name() or request.user.username}"""

    context = {
        'invoice': invoice,
        'tax_amount': tax_amount,
        'due_date_str': due_date_str,
        'default_subject': default_subject,
        'default_body': default_body,
    }
    return render(request, 'invoicing/invoice_detail.html', context)


@login_required
def mark_invoice_paid(request, invoice_id):
    """Mark invoice as paid"""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, id=invoice_id)
        old_status = invoice.status
        invoice.status = 'paid'
        invoice.payment_received_date = timezone.now().date()
        invoice.payment_notes = request.POST.get('payment_notes', 'Marked as paid via dashboard')
        invoice.save()
        
        # Create history record
        InvoiceHistory.objects.create(
            invoice=invoice,
            old_status=old_status,
            new_status='paid',
            changed_by=request.user,
            notes=f"Payment received on {invoice.payment_received_date}"
        )
        
        return JsonResponse({'success': True, 'message': 'Invoice marked as paid'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})



@login_required
def download_invoice_pdf(request, invoice_id):
    """Generate and download invoice as PDF"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Calculate tax amount
    tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
    
    # Company Header
    title = Paragraph("INVOICE", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Invoice Information
    invoice_info = f"""
    <para align="left">
    <b>Invoice Number:</b> {invoice.invoice_number}<br/>
    <b>Issue Date:</b> {invoice.issue_date}<br/>
    <b>Due Date:</b> {invoice.due_date or 'Not Set'}<br/>
    <b>Status:</b> {invoice.get_status_display()}
    </para>
    """
    elements.append(Paragraph(invoice_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Bill To Section
    bill_to = f"""
    <para align="left">
    <b>BILL TO:</b><br/>
    <b>{invoice.placement.client.name}</b><br/>
    {invoice.placement.client.contact_person}<br/>
    {invoice.placement.client.address}<br/>
    Email: {invoice.placement.client.email}<br/>
    Phone: {invoice.placement.client.phone or 'N/A'}
    </para>
    """
    elements.append(Paragraph(bill_to, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Service Details
    service_details = f"""
    <para align="left">
    <b>SERVICE DETAILS:</b><br/>
    Candidate: {invoice.placement.candidate.name}<br/>
    Position: {invoice.placement.position}<br/>
    Joining Date: {invoice.placement.joining_date}<br/>
    Notice Period: {invoice.placement.notice_period_days} days
    </para>
    """
    elements.append(Paragraph(service_details, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Invoice Table
    data = [
        ['Description', 'Amount (₹)'],
        [f'Recruitment Service Fee\nPlacement of {invoice.placement.candidate.name} as {invoice.placement.position}', f'{invoice.amount:,.2f}'],
        [f'Tax ({invoice.tax_rate}%)', f'{tax_amount:,.2f}'],
        ['', ''],  # Empty row for spacing
        ['TOTAL AMOUNT', f'{invoice.total_amount:,.2f}']
    ]
    
    table = Table(data, colWidths=[4*inch, 2*inch])
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align amounts
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -3), colors.white),
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -3), 10),
        
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        
        # Grid
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer = Paragraph("Thank you for your business!", styles['Normal'])
    elements.append(footer)
    
    # Build the PDF
    doc.build(elements)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    response['Content-Length'] = len(pdf_data)
    
    return response


@login_required


def send_invoice_email(request, invoice_id):
    """Send invoice via email"""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        subject = request.POST.get('email_subject')
        body = request.POST.get('email_body')
        
        try:
            # Generate PDF attachment
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=1*inch)
            
            # Container for PDF elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Calculate tax amount
            tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
            
            # Company Header
            title = Paragraph("INVOICE", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # Invoice Information
            invoice_info = f"""
            <para align="left">
            <b>Invoice Number:</b> {invoice.invoice_number}<br/>
            <b>Issue Date:</b> {invoice.issue_date}<br/>
            <b>Due Date:</b> {invoice.due_date or 'Not Set'}<br/>
            <b>Status:</b> {invoice.get_status_display()}
            </para>
            """
            elements.append(Paragraph(invoice_info, styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Bill To Section
            bill_to = f"""
            <para align="left">
            <b>BILL TO:</b><br/>
            <b>{invoice.placement.client.name}</b><br/>
            {invoice.placement.client.contact_person}<br/>
            {invoice.placement.client.address}<br/>
            Email: {invoice.placement.client.email}<br/>
            Phone: {invoice.placement.client.phone or 'N/A'}
            </para>
            """
            elements.append(Paragraph(bill_to, styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Service Details
            service_details = f"""
            <para align="left">
            <b>SERVICE DETAILS:</b><br/>
            Candidate: {invoice.placement.candidate.name}<br/>
            Position: {invoice.placement.position}<br/>
            Joining Date: {invoice.placement.joining_date}<br/>
            Notice Period: {invoice.placement.notice_period_days} days
            </para>
            """
            elements.append(Paragraph(service_details, styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Invoice Table
            data = [
                ['Description', 'Amount (₹)'],
                [f'Recruitment Service Fee\nPlacement of {invoice.placement.candidate.name} as {invoice.placement.position}', f'{invoice.amount:,.2f}'],
                [f'Tax ({invoice.tax_rate}%)', f'{tax_amount:,.2f}'],
                ['', ''],  # Empty row for spacing
                ['TOTAL AMOUNT', f'{invoice.total_amount:,.2f}']
            ]
            
            table = Table(data, colWidths=[4*inch, 2*inch])
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align amounts
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -3), colors.white),
                ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -3), 10),
                
                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                
                # Grid
                ('GRID', (0, 0), (-1, -2), 1, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 30))
            
            # Footer
            footer = Paragraph("Thank you for your business!", styles['Normal'])
            elements.append(footer)
            
            # Build the PDF ONCE
            doc.build(elements)
            
            # Get the PDF data
            pdf_data = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invoice.placement.client.email],
                reply_to=[request.user.email] if request.user.email else None,
            )
            
            # Attach PDF
            email.attach(
                f'invoice_{invoice.invoice_number}.pdf',
                pdf_data,
                'application/pdf'
            )
            
            # Send email
            email.send()
            
            # Update invoice status after successful send
            old_status = invoice.status
            invoice.status = 'sent'
            invoice.sent_at = timezone.now()
            invoice.sent_by = request.user
            invoice.email_subject = subject
            invoice.email_body = body
            invoice.save()
            
            # Create history record
            InvoiceHistory.objects.create(
                invoice=invoice,
                old_status=old_status,
                new_status='sent',
                changed_by=request.user,
                notes=f"Invoice sent to {invoice.placement.client.email}"
            )
            
            return JsonResponse({'success': True, 'message': 'Invoice sent successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Failed to send email: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required

def invoice_list(request):
    """Show both recruitment and general invoices with filtering"""
    
    # Get all recruitment invoices
    recruitment_invoices = Invoice.objects.all().order_by('-created_at')
    
    # Get all general invoices
    general_invoices = GeneralInvoice.objects.all().order_by('-created_at')
    
    # Add search functionality
    search = request.GET.get('search')
    if search:
        recruitment_invoices = recruitment_invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(placement__candidate__name__icontains=search) |
            Q(placement__client__name__icontains=search)
        )
        general_invoices = general_invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(client_name__icontains=search) |
            Q(service_description__icontains=search)
        )
    
    # Add status filtering
    status = request.GET.get('status')
    if status:
        recruitment_invoices = recruitment_invoices.filter(status=status)
        general_invoices = general_invoices.filter(status=status)
    
    # Add type filtering
    invoice_type = request.GET.get('type')
    if invoice_type == 'recruitment':
        general_invoices = GeneralInvoice.objects.none()
    elif invoice_type == 'general':
        recruitment_invoices = Invoice.objects.none()
    
    # Combine them for display
    all_invoices = []
    
    # Add recruitment invoices with type indicator
    for inv in recruitment_invoices:
        if inv.id and inv.placement and inv.placement.client:  # Safety checks
            try:
                detail_url = reverse('invoicing:invoice_detail', args=[inv.id])
            except:
                detail_url = '#'
                
            all_invoices.append({
                'invoice': inv,
                'type': 'recruitment',
                'client_name': inv.placement.client.name,
                'detail_url': detail_url
            })
    
    # Add general invoices with type indicator
    for inv in general_invoices:
        if inv.id and inv.client_name:  # Safety checks
            try:
                detail_url = reverse('invoicing:general_invoice_detail', args=[inv.id])
            except:
                detail_url = '#'
                
            all_invoices.append({
                'invoice': inv,
                'type': 'general',
                'client_name': inv.client_name,
                'detail_url': detail_url
            })
    
    # Sort by creation date (most recent first)
    all_invoices.sort(key=lambda x: x['invoice'].created_at, reverse=True)
    
    context = {
        'invoices': all_invoices,
        'status_choices': Invoice.STATUS_CHOICES,
        'recruitment_count': recruitment_invoices.count(),
        'general_count': general_invoices.count(),
        'current_search': search,
        'current_status': status,
        'current_type': invoice_type,
        'today': timezone.now().date(),
        'breadcrumb_list': [
            {'name': 'Horilla', 'url': '/'},
            {'name': 'Invoicing', 'url': '/invoicing/dashboard/'},
            {'name': 'Invoices', 'url': ''}
        ]
    }
    return render(request, 'invoicing/invoice_list.html', context)

@login_required 
def general_invoice_create(request):
    """Create general business invoice"""
    if request.method == 'POST':
        form = GeneralInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.sent_by = request.user
            invoice.save()
            messages.success(request, f'General Invoice {invoice.invoice_number} created successfully!')
            return redirect('invoicing:general_invoice_detail', invoice.id)
    else:
        form = GeneralInvoiceForm()
    
    context = {
        'form': form,
        'title': 'Create General Invoice'
    }
    return render(request, 'invoicing/general_invoice_form.html', context)

def general_invoice_detail(request, invoice_id):
    """Show general invoice details"""
    invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
    
    # Calculate tax amount
    tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
    
    # Handle None due_date
    due_date_str = invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'
    
    context = {
        'invoice': invoice,
        'tax_amount': tax_amount,
        'due_date_str': due_date_str,
        'title': f'General Invoice {invoice.invoice_number}'
    }
    return render(request, 'invoicing/general_invoice_detail.html', context)
@login_required
def general_invoice_pdf(request, invoice_id):
    """Generate and download general invoice as PDF"""
    invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
    
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Calculate tax amount
    tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
    
    # Company Header
    title = Paragraph("GENERAL INVOICE", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Invoice Information
    invoice_info = f"""
    <para align="left">
    <b>Invoice Number:</b> {invoice.invoice_number}<br/>
    <b>Issue Date:</b> {invoice.issue_date}<br/>
    <b>Due Date:</b> {invoice.due_date or 'Not Set'}<br/>
    <b>Status:</b> {invoice.get_status_display()}
    </para>
    """
    elements.append(Paragraph(invoice_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Bill To Section
    bill_to = f"""
    <para align="left">
    <b>BILL TO:</b><br/>
    <b>{invoice.client_name}</b><br/>
    {invoice.client_address}<br/>
    Email: {invoice.client_email}<br/>
    Phone: {invoice.client_phone or 'N/A'}
    </para>
    """
    elements.append(Paragraph(bill_to, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Service Details
    service_details = f"""
    <para align="left">
    <b>SERVICE DESCRIPTION:</b><br/>
    {invoice.service_description}
    </para>
    """
    elements.append(Paragraph(service_details, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Invoice Table
    data = [
        ['Description', 'Amount (₹)'],
        [invoice.service_description, f'{invoice.amount:,.2f}'],
        [f'Tax ({invoice.tax_rate}%)', f'{tax_amount:,.2f}'],
        ['', ''],  # Empty row for spacing
        ['TOTAL AMOUNT', f'{invoice.total_amount:,.2f}']
    ]
    
    table = Table(data, colWidths=[4*inch, 2*inch])
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align amounts
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -3), colors.white),
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -3), 10),
        
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        
        # Grid
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer = Paragraph("Thank you for your business!", styles['Normal'])
    elements.append(footer)
    
    # Build the PDF
    doc.build(elements)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="general_invoice_{invoice.invoice_number}.pdf"'
    response['Content-Length'] = len(pdf_data)
    
    return response
def general_invoice_mark_paid(request, invoice_id):
    """Mark general invoice as paid"""
    if request.method == 'POST':
        invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
        old_status = invoice.status
        invoice.status = 'paid'
        invoice.payment_received_date = timezone.now().date()
        invoice.payment_notes = request.POST.get('payment_notes', 'Marked as paid via dashboard')
        invoice.save()
        
        return JsonResponse({'success': True, 'message': 'General invoice marked as paid'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def react_invoice_view(request):
    return render(request, 'invoicing/invoice_react.html')