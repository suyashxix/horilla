from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q
from networkx import reverse
from .models import Client, Candidate, GeneralInvoice, Placement, Invoice, InvoiceNotification, InvoiceHistory
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
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from datetime import date, timedelta
from django.conf import settings
import os
from django.core.files.base import ContentFile

@login_required
def dashboard(request):
    """Dashboard view with proper data for both recruitment and general invoices"""
    try:
        # Get all placements
        placements = Placement.objects.select_related('candidate', 'client').all()
        
        # Get eligible placements (those ready for invoice creation)
        eligible_placements = []
        for placement in placements:
            if placement.is_invoice_eligible:
                # Check if invoice already exists
                try:
                    Invoice.objects.get(placement=placement)
                except Invoice.DoesNotExist:
                    eligible_placements.append(placement)
        
        # Get recruitment invoices
        recruitment_invoices = Invoice.objects.select_related(
            'placement__candidate', 
            'placement__client'
        ).all()
        
        # Get general invoices
        general_invoices = GeneralInvoice.objects.all()
        
        # Combine both types of invoices for recent invoices display
        recent_invoices = []
        
        # Add recruitment invoices with type
        for invoice in recruitment_invoices.order_by('-created_at')[:10]:
            recent_invoices.append({
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total_amount': invoice.total_amount,
                'status': invoice.status,
                'created_at': invoice.created_at,
                'type': 'recruitment',
                'placement': invoice.placement,
                'get_status_display': invoice.get_status_display() if hasattr(invoice, 'get_status_display') else invoice.status.title()
            })
        
        # Add general invoices with type
        for invoice in general_invoices.order_by('-created_at')[:10]:
            recent_invoices.append({
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total_amount': invoice.total_amount,
                'status': invoice.status,
                'created_at': invoice.created_at,
                'type': 'general',
                'client_name': invoice.client_name,
                'get_status_display': invoice.get_status_display() if hasattr(invoice, 'get_status_display') else invoice.status.title()
            })
        
        # Sort combined invoices by creation date
        recent_invoices.sort(key=lambda x: x['created_at'], reverse=True)
        recent_invoices = recent_invoices[:10]  # Keep only 10 most recent
        
        # Get clients
        clients = Client.objects.filter(is_active=True)
        
        # Calculate revenue statistics
        recruitment_revenue = sum([inv.total_amount for inv in recruitment_invoices if inv.status == 'paid'])
        general_revenue = sum([inv.total_amount for inv in general_invoices if inv.status == 'paid'])
        total_revenue = recruitment_revenue + general_revenue
        
        pending_recruitment = sum([inv.total_amount for inv in recruitment_invoices if inv.status in ['draft', 'sent']])
        pending_general = sum([inv.total_amount for inv in general_invoices if inv.status in ['draft', 'sent']])
        pending_revenue = pending_recruitment + pending_general
        
        total_invoices_count = recruitment_invoices.count() + general_invoices.count()
        avg_invoice_value = total_revenue / total_invoices_count if total_invoices_count > 0 else 0
        
        # Calculate statistics
        stats = {
            'total_placements': placements.count(),
            'eligible_placements': len(eligible_placements),
            'total_invoices': total_invoices_count,
            'total_clients': clients.count(),
            'recruitment_invoices': recruitment_invoices.count(),
            'general_invoices': general_invoices.count(),
            'draft_invoices': recruitment_invoices.filter(status='draft').count() + general_invoices.filter(status='draft').count(),
            'sent_invoices': recruitment_invoices.filter(status='sent').count() + general_invoices.filter(status='sent').count(),
            'paid_invoices': recruitment_invoices.filter(status='paid').count() + general_invoices.filter(status='paid').count(),
            'overdue_invoices': recruitment_invoices.filter(status='overdue').count() + general_invoices.filter(status='overdue').count(),
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
            'avg_invoice_value': avg_invoice_value,
        }
        
        context = {
            'eligible_placements': eligible_placements,
            'recent_invoices': recent_invoices,
            'stats': stats,
        }
        
        return render(request, 'invoicing/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'invoicing/dashboard.html', {
            'eligible_placements': [],
            'recent_invoices': [],
            'stats': {
                'total_placements': 0,
                'eligible_placements': 0,
                'total_invoices': 0,
                'total_clients': 0,
                'recruitment_invoices': 0,
                'general_invoices': 0,
                'draft_invoices': 0,
                'sent_invoices': 0,
                'paid_invoices': 0,
                'overdue_invoices': 0,
                'total_revenue': 0,
                'pending_revenue': 0,
                'avg_invoice_value': 0,
            }
        })
    
@login_required
def client_list(request):
    """List all clients with statistics"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    clients = Client.objects.all().order_by('name')
    
    # Calculate statistics
    active_clients_count = clients.filter(is_active=True).count()
    
    # Clients added this month
    this_month = timezone.now().replace(day=1)
    recent_clients_count = clients.filter(created_at__gte=this_month).count()
    
    # Clients with invoices (both recruitment and general)
    clients_with_invoices = set()
    for invoice in Invoice.objects.all():
        if invoice.placement and invoice.placement.client:
            clients_with_invoices.add(invoice.placement.client.id)
    for invoice in GeneralInvoice.objects.all():
        # For general invoices, we match by client name
        matching_clients = clients.filter(name__icontains=invoice.client_name)
        for client in matching_clients:
            clients_with_invoices.add(client.id)
    
    context = {
        'clients': clients,
        'active_clients_count': active_clients_count,
        'recent_clients_count': recent_clients_count,
        'clients_with_invoices': len(clients_with_invoices),
    }
    return render(request, 'invoicing/Client/client_list.html', context)

@login_required
def client_create(request):
    """Create new client"""
    if request.method == 'POST':
        try:
            # Validate required fields
            name = request.POST.get('name')
            email = request.POST.get('email')
            contact_person = request.POST.get('contact_person')
            address = request.POST.get('address')
            
            if not all([name, email, contact_person, address]):
                error_msg = '❌ Please fill in all required fields (Name, Email, Contact Person, Address).'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return render(request, 'invoicing/Client/client_form.html', {'form_action': 'create'})
            
            client = Client.objects.create(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=request.POST.get('phone', ''),
                address=address,
                is_active=True
            )
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'id': client.id,
                    'name': client.name,
                    'contact_person': client.contact_person,
                    'email': client.email
                })
            
            messages.success(request, f'✅ Client "{client.name}" has been created successfully!')
            return redirect('invoicing:client_detail', client_id=client.id)
            
        except Exception as e:
            error_msg = f'❌ Error creating client: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            
            messages.error(request, error_msg)
    
    # GET request - show form
    return render(request, 'invoicing/Client/client_form.html', {'form_action': 'create'})
@login_required
def placement_list(request):
    """List all placements"""
    try:
        # Get all placements with related data
        placements = Placement.objects.select_related('candidate', 'client').all()
        
        placement_data = []
        for placement in placements:
            # Check if placement has an invoice
            try:
                invoice = Invoice.objects.get(placement=placement)
                has_invoice = True
            except Invoice.DoesNotExist:
                has_invoice = False
                invoice = None
            
            # Get days until eligible (ensure it's an integer)
            days_until = placement.days_until_eligible_invoice
            
            placement_data.append({
                'placement': placement,
                'has_invoice': has_invoice,
                'invoice': invoice,
                'is_eligible': placement.is_invoice_eligible,
                'days_until_eligible': days_until,  # Now it's an integer
            })
        
        # Get clients for filter dropdown
        clients = Client.objects.filter(is_active=True)
        
        context = {
            'placement_data': placement_data,
            'clients': clients,
        }
        
        return render(request, 'invoicing/placements/placement_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading placements: {str(e)}')
        return render(request, 'invoicing/placements/placement_list.html', {'placement_data': [], 'clients': []})

@login_required

def invoice_create(request, placement_id):
    """Create invoice for a placement - AUTO GENERATES PDF"""
    try:
        placement = get_object_or_404(Placement, id=placement_id)
        
        # Check if invoice already exists
        existing_invoice = Invoice.objects.filter(placement=placement).first()
        if existing_invoice:
            messages.warning(request, 'Invoice already exists for this placement.')
            return redirect('invoicing:invoice_detail', invoice_id=existing_invoice.id)
        
        # Check if placement is eligible
        if not placement.is_invoice_eligible:
            eligible_date = placement.invoice_eligible_date.strftime("%B %d, %Y")
            messages.error(request, f'Placement is not yet eligible for invoicing. Eligible on {eligible_date}')
            return redirect('invoicing:placement_list')
        
        if request.method == 'POST':
            # Get form data
            tax_rate = Decimal(str(request.POST.get('tax_rate', '18.0')))
            due_days = int(request.POST.get('due_days', 30))
            
            # Create invoice
            invoice = Invoice.objects.create(
                placement=placement,
                amount=placement.placement_fee,
                tax_rate=tax_rate,
                status='draft'
            )
            
            # Set due date
            if due_days > 0:
                invoice.due_date = invoice.issue_date + timedelta(days=due_days)
                invoice.save()
            
            # AUTOMATICALLY GENERATE AND SAVE PDF
            try:
                pdf_content = generate_invoice_pdf(invoice)
                invoice.save_generated_pdf(pdf_content)
                pdf_generated = True
            except Exception as pdf_error:
                print(f"PDF generation failed: {pdf_error}")
                pdf_generated = False
            
            # Update placement status
            placement.status = 'invoiced'
            placement.save()
            
            # Success message
            success_msg = f"Invoice {invoice.invoice_number} created successfully!"
            if pdf_generated:
                success_msg += " PDF has been generated and saved."
            
            messages.success(request, success_msg)
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice_id': invoice.id,
                    'invoice_number': str(invoice.invoice_number),
                    'redirect_url': f'/invoicing/invoices/{invoice.id}/',
                    'pdf_generated': pdf_generated
                })
            
            return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
        
        # GET request - show form
        context = {
            'placement': placement,
            'candidate': placement.candidate,
            'client': placement.client,
        }
        
        return render(request, 'invoicing/Invoicing/invoice_create.html', context)
        
    except Exception as e:
        error_msg = f'Error creating invoice: {str(e)}'
        print(f"Full error: {e}")  # For debugging
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        
        messages.error(request, error_msg)
        return redirect('invoicing:placement_list')

def generate_invoice_pdf(invoice):
    """Generate PDF content for invoice"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=0.8*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.8*inch,
        rightMargin=0.8*inch
    )
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Calculate tax amount
    tax_amount = Decimal('0')
    if invoice.amount and invoice.tax_rate:
        tax_amount = (invoice.amount * invoice.tax_rate) / Decimal('100')
    
    # Title
    title = Paragraph("RECRUITMENT INVOICE", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 30))
    
    # Invoice info table
    invoice_info_data = [
        ['Invoice Number:', str(invoice.invoice_number), 'Issue Date:', invoice.issue_date.strftime('%B %d, %Y')],
        ['Status:', invoice.get_status_display(), 'Due Date:', invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'],
    ]
    
    invoice_info_table = Table(invoice_info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    invoice_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(invoice_info_table)
    elements.append(Spacer(1, 30))
    
    # Bill To and Service Provider
    bill_service_data = [
        ['BILL TO:', 'SERVICE PROVIDER:'],
        [
            f"{invoice.placement.client.name}\n{invoice.placement.client.contact_person}\n{invoice.placement.client.address}\nEmail: {invoice.placement.client.email}\nPhone: {invoice.placement.client.phone or 'N/A'}",
            "Your Company Name\nYour Address\nYour City, State, ZIP\nEmail: your-email@company.com\nPhone: Your Phone Number"
        ]
    ]
    
    bill_service_table = Table(bill_service_data, colWidths=[3.5*inch, 3.5*inch])
    bill_service_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
    ]))
    
    elements.append(bill_service_table)
    elements.append(Spacer(1, 30))
    
    # Service Details
    service_header = Paragraph("<b>SERVICE DETAILS</b>", styles['Heading2'])
    elements.append(service_header)
    elements.append(Spacer(1, 10))
    
    service_details = f"""
    <para>
    <b>Candidate:</b> {invoice.placement.candidate.name}<br/>
    <b>Position:</b> {invoice.placement.position}<br/>
    <b>Joining Date:</b> {invoice.placement.joining_date.strftime('%B %d, %Y')}<br/>
    <b>Notice Period:</b> {invoice.placement.notice_period_days} days<br/>
    <b>Placement Type:</b> {invoice.placement.get_placement_type_display()}
    </para>
    """
    elements.append(Paragraph(service_details, styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Invoice Items Table
    table_data = [
        ['Description', 'Amount (₹)'],
        [f"Recruitment Service Fee\nPlacement of {invoice.placement.candidate.name}\nPosition: {invoice.placement.position}", f"{float(invoice.amount):,.2f}"],
    ]
    
    if tax_amount > 0:
        table_data.append([f"Tax ({float(invoice.tax_rate)}%)", f"{float(tax_amount):,.2f}"])
    
    table_data.append(['', ''])
    table_data.append(['TOTAL AMOUNT', f"₹{float(invoice.total_amount):,.2f}"])
    
    invoice_table = Table(table_data, colWidths=[4.5*inch, 2.5*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -3), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -3), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(invoice_table)
    elements.append(Spacer(1, 40))
    
    # Payment Instructions
    payment_instructions = f"""
    <para>
    <b>PAYMENT INSTRUCTIONS:</b><br/>
    Please process payment by {invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else '30 days from issue date'}.
    Reference invoice number {invoice.invoice_number} in your payment.
    </para>
    """
    elements.append(Paragraph(payment_instructions, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = """
    <para align="center">
    <b>Thank you for your business!</b><br/>
    For questions regarding this invoice, please contact us immediately.
    </para>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data and close buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

@login_required
def invoice_upload_pdf(request, invoice_id):
    """Upload custom PDF to replace generated one"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if request.method == 'POST' and request.FILES.get('pdf_file'):
            uploaded_file = request.FILES['pdf_file']
            
            # Validate file type
            if not uploaded_file.name.lower().endswith('.pdf'):
                messages.error(request, 'Please upload a PDF file only.')
                return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
            
            # Replace PDF
            invoice.replace_pdf(uploaded_file, request.user)
            
            messages.success(request, f'Custom PDF uploaded successfully for invoice {invoice.invoice_number}!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'PDF uploaded successfully',
                    'pdf_url': invoice.pdf_file.url if invoice.pdf_file else None
                })
        
        return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
        
    except Exception as e:
        error_msg = f'Error uploading PDF: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        
        messages.error(request, error_msg)
        return redirect('invoicing:invoice_detail', invoice_id=invoice_id)
    
@login_required
def invoice_download_pdf(request, invoice_id):
    """Download invoice PDF"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Check if PDF exists
        if not invoice.pdf_file:
            # Generate PDF if not exists
            try:
                pdf_content = generate_invoice_pdf(invoice)
                invoice.save_generated_pdf(pdf_content)
            except Exception as e:
                messages.error(request, f'Error generating PDF: {str(e)}')
                return redirect('invoicing:invoice_detail', invoice_id=invoice_id)
        
        # Create response
        try:
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_number}.pdf"'
            
            # Read file content
            invoice.pdf_file.open('rb')
            response.write(invoice.pdf_file.read())
            invoice.pdf_file.close()
            
            return response
            
        except Exception as e:
            messages.error(request, f'Error opening PDF file: {str(e)}')
            return redirect('invoicing:invoice_detail', invoice_id=invoice_id)
        
    except Exception as e:
        messages.error(request, f'Error downloading PDF: {str(e)}')
        return redirect('invoicing:invoice_detail', invoice_id=invoice_id)
@login_required
def invoice_detail(request, invoice_id):
    """Show invoice details - COMPLETELY OVERHAULED"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Handle POST requests for actions
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'mark_paid':
                # Handle mark as paid directly here
                old_status = invoice.status
                payment_date = request.POST.get('payment_date')
                payment_notes = request.POST.get('payment_notes', '')
                
                invoice.status = 'paid'
                if payment_date:
                    from datetime import datetime
                    invoice.payment_received_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                else:
                    invoice.payment_received_date = timezone.now().date()
                
                invoice.payment_notes = payment_notes
                invoice.save()
                
                messages.success(request, f'✅ Invoice {invoice.invoice_number} marked as paid successfully!')
                return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
                
            elif action == 'send_email':
                # Redirect to send email function
                return redirect('invoicing:send_invoice_email', invoice_id=invoice.id)
        
        if invoice.amount and invoice.tax_rate:
            amount = Decimal(str(invoice.amount))
            tax_rate = Decimal(str(invoice.tax_rate))
            tax_amount = (amount * tax_rate) / Decimal('100')
        else:
            tax_amount = Decimal('0')
        
        # Convert back to float for template display if needed
        tax_amount = float(tax_amount)
        
        # Handle date formatting safely
        due_date_str = invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'
        issue_date_str = invoice.issue_date.strftime('%B %d, %Y') if invoice.issue_date else 'Not Set'
        
        # Check if invoice is overdue
        is_overdue = False
        days_overdue = 0
        if invoice.due_date and invoice.status not in ['paid', 'cancelled']:
            today = timezone.now().date()
            if today > invoice.due_date:
                is_overdue = True
                days_overdue = (today - invoice.due_date).days
        
        # Prepare default email content
        client_contact = 'Valued Client'
        if invoice.placement and invoice.placement.client:
            client_contact = invoice.placement.client.contact_person or invoice.placement.client.name
        
        default_subject = f"Invoice {invoice.invoice_number} - Recruitment Services"
        default_body = f"""Dear {client_contact},

I hope this email finds you well.

Please find attached the invoice for the successful placement of {invoice.placement.candidate.name} for the position of {invoice.placement.position} at {invoice.placement.client.name}.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Candidate: {invoice.placement.candidate.name}
- Position: {invoice.placement.position}
- Placement Fee: ₹{invoice.amount:,.2f}
- Tax ({invoice.tax_rate}%): ₹{tax_amount:,.2f}
- Total Amount: ₹{invoice.total_amount:,.2f}
- Issue Date: {issue_date_str}
- Due Date: {due_date_str}

Payment Details:
Please process the payment within the due date to avoid any late fees.

Thank you for your business.

Best regards,
{request.user.get_full_name() or request.user.username}
Recruitment Team"""

        context = {
            'invoice': invoice,
            'placement': invoice.placement,
            'candidate': invoice.placement.candidate if invoice.placement else None,
            'client': invoice.placement.client if invoice.placement else None,
            'tax_amount': tax_amount,
            'due_date_str': due_date_str,
            'issue_date_str': issue_date_str,
            'default_subject': default_subject,
            'default_body': default_body,
            'is_overdue': is_overdue,
            'days_overdue': days_overdue,
        }
        
        # FIXED: Use correct template path based on your structure
        return render(request, 'invoicing/Invoicing/invoice_detail.html', context)
        
    except Invoice.DoesNotExist:
        messages.error(request, '❌ Invoice not found.')
        return redirect('invoicing:invoice_list')
    except Exception as e:
        messages.error(request, f'❌ Error loading invoice: {str(e)}')
        return redirect('invoicing:invoice_list')


@login_required
def mark_invoice_paid(request, invoice_id):
    """Mark invoice as paid"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if request.method == 'POST':
            old_status = invoice.status
            payment_date = request.POST.get('payment_date')
            payment_notes = request.POST.get('payment_notes', '')
            
            # Update invoice
            invoice.status = 'paid'
            if payment_date:
                from datetime import datetime
                invoice.payment_received_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            else:
                invoice.payment_received_date = timezone.now().date()
            
            invoice.payment_notes = payment_notes
            invoice.save()
            
            # Create history entry
            InvoiceHistory.objects.create(
                invoice=invoice,
                old_status=old_status,
                new_status='paid',
                changed_by=request.user,
                notes=f"Payment received. {payment_notes}"
            )
            
            # Update placement status
            if invoice.placement.status == 'invoiced':
                invoice.placement.status = 'completed'
                invoice.placement.save()
            
            messages.success(request, f'✅ Invoice {invoice.invoice_number} marked as paid successfully!')
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Invoice marked as paid',
                    'new_status': 'paid'
                })
        
        return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
        
    except Exception as e:
        error_msg = f'Error marking invoice as paid: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        
        messages.error(request, f'❌ {error_msg}')
        return redirect('invoicing:invoice_detail', invoice_id=invoice_id)
    


@login_required
def send_invoice_email(request, invoice_id):
    """Send invoice via email with PDF attachment"""
    if request.method == 'POST':
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id)
            
            # Get email data from form
            subject = request.POST.get('email_subject', '').strip()
            body = request.POST.get('email_body', '').strip()
            recipient_email = request.POST.get('recipient_email', '').strip()
            
            # Use client email as fallback
            if not recipient_email:
                recipient_email = invoice.placement.client.email
            
            # Validation
            if not subject:
                return JsonResponse({'success': False, 'message': 'Email subject is required'})
            
            if not body:
                return JsonResponse({'success': False, 'message': 'Email body is required'})
            
            if not recipient_email:
                return JsonResponse({'success': False, 'message': 'Recipient email is required'})
            
            # Generate PDF attachment
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer, 
                pagesize=A4, 
                topMargin=0.8*inch,
                bottomMargin=0.8*inch,
                leftMargin=0.8*inch,
                rightMargin=0.8*inch
            )
            
            # Container for PDF elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Calculate amounts
            tax_amount = (invoice.amount * invoice.tax_rate) / 100 if invoice.amount and invoice.tax_rate else 0
            
            # Custom styles
            title_style = styles['Title']
            title_style.fontSize = 24
            title_style.spaceAfter = 30
            
            normal_style = styles['Normal']
            normal_style.fontSize = 10
            normal_style.leading = 14
            
            # Company Header
            title = Paragraph("RECRUITMENT INVOICE", title_style)
            elements.append(title)
            
            # Invoice Information Table
            invoice_info_data = [
                ['Invoice Number:', invoice.invoice_number, 'Issue Date:', invoice.issue_date.strftime('%B %d, %Y') if invoice.issue_date else 'N/A'],
                ['Status:', invoice.get_status_display(), 'Due Date:', invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'],
            ]
            
            invoice_info_table = Table(invoice_info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
            invoice_info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels bold
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Labels bold
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(invoice_info_table)
            elements.append(Spacer(1, 30))
            
            # Bill To and Service Provider sections
            bill_service_data = [
                ['BILL TO:', 'SERVICE PROVIDER:'],
                [
                    f"""{invoice.placement.client.name}
{invoice.placement.client.contact_person}
{invoice.placement.client.address}
Email: {invoice.placement.client.email}
Phone: {invoice.placement.client.phone or 'N/A'}""",
                    f"""Your Company Name
Your Address
Your City, State, ZIP
Email: {settings.DEFAULT_FROM_EMAIL}
Phone: Your Phone Number"""
                ]
            ]
            
            bill_service_table = Table(bill_service_data, colWidths=[3.5*inch, 3.5*inch])
            bill_service_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, 1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ]))
            
            elements.append(bill_service_table)
            elements.append(Spacer(1, 30))
            
            # Service Details Section
            service_header = Paragraph("<b>SERVICE DETAILS</b>", styles['Heading2'])
            elements.append(service_header)
            elements.append(Spacer(1, 10))
            
            service_details = f"""
            <para>
            <b>Candidate:</b> {invoice.placement.candidate.name}<br/>
            <b>Position:</b> {invoice.placement.position}<br/>
            <b>Joining Date:</b> {invoice.placement.joining_date.strftime('%B %d, %Y')}<br/>
            <b>Notice Period:</b> {invoice.placement.notice_period_days} days<br/>
            <b>Placement Type:</b> {invoice.placement.get_placement_type_display()}
            </para>
            """
            elements.append(Paragraph(service_details, normal_style))
            elements.append(Spacer(1, 30))
            
            # Invoice Items Table
            items_header = Paragraph("<b>INVOICE BREAKDOWN</b>", styles['Heading2'])
            elements.append(items_header)
            elements.append(Spacer(1, 10))
            
            # Prepare table data
            table_data = [
                ['Description', 'Amount (₹)']
            ]
            
            # Service description
            service_desc = f"Recruitment Service Fee\nSuccessful placement of {invoice.placement.candidate.name}\nPosition: {invoice.placement.position}"
            table_data.append([service_desc, f"{invoice.amount:,.2f}"])
            
            # Tax row
            if tax_amount > 0:
                table_data.append([f"Tax ({invoice.tax_rate}%)", f"{tax_amount:,.2f}"])
            
            # Separator row
            table_data.append(['', ''])
            
            # Total row
            table_data.append(['TOTAL AMOUNT', f"₹{invoice.total_amount:,.2f}"])
            
            # Create table
            invoice_table = Table(table_data, colWidths=[4.5*inch, 2.5*inch])
            invoice_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -3), colors.white),
                ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -3), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -3), 8),
                
                # Separator row (invisible)
                ('LINEBELOW', (0, -2), (-1, -2), 0, colors.white),
                
                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
                
                # Grid lines
                ('GRID', (0, 0), (-1, -3), 1, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ]))
            
            elements.append(invoice_table)
            elements.append(Spacer(1, 40))
            
            # Payment Instructions
            payment_instructions = f"""
            <para>
            <b>PAYMENT INSTRUCTIONS:</b><br/>
            Please process payment within {invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else '30 days'}.
            Payment can be made via bank transfer or online payment methods.
            Please reference invoice number {invoice.invoice_number} in your payment.
            </para>
            """
            elements.append(Paragraph(payment_instructions, normal_style))
            elements.append(Spacer(1, 20))
            
            # Footer
            footer_text = """
            <para align="center">
            <b>Thank you for your business!</b><br/>
            For any questions regarding this invoice, please contact us immediately.
            </para>
            """
            elements.append(Paragraph(footer_text, normal_style))
            
            # Build the PDF
            doc.build(elements)
            
            # Get the PDF data
            pdf_data = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[request.user.email] if request.user.email else [settings.DEFAULT_FROM_EMAIL],
            )
            
            # Attach PDF
            filename = f"Invoice_{invoice.invoice_number}_{invoice.placement.client.name.replace(' ', '_')}.pdf"
            email.attach(filename, pdf_data, 'application/pdf')
            
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
                notes=f"Invoice sent to {recipient_email}"
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Invoice sent successfully to {recipient_email}',
                'new_status': 'sent',
                'sent_at': timezone.now().strftime('%B %d, %Y at %I:%M %p')
            })
            
        except Exception as e:
            # Log the error for debugging
            import traceback
            error_details = traceback.format_exc()
            print(f"Email sending error: {error_details}")
            
            return JsonResponse({
                'success': False, 
                'message': f'Failed to send email: {str(e)}',
                'error_details': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def invoice_list(request):
    """Show both recruitment and general invoices with filtering"""
    try:
        # Get all recruitment invoices
        recruitment_invoices = Invoice.objects.select_related(
            'placement__candidate', 
            'placement__client'
        ).all().order_by('-created_at')
        
        # Get all general invoices
        general_invoices = GeneralInvoice.objects.all().order_by('-created_at')
        
        # Add search functionality
        search = request.GET.get('search', '').strip()
        if search:
            recruitment_invoices = recruitment_invoices.filter(
                Q(invoice_number__icontains=search) |
                Q(placement__candidate__name__icontains=search) |
                Q(placement__client__name__icontains=search) |
                Q(placement__position__icontains=search)
            )
            general_invoices = general_invoices.filter(
                Q(invoice_number__icontains=search) |
                Q(client_name__icontains=search) |
                Q(service_description__icontains=search)
            )
        
        # Add status filtering
        status = request.GET.get('status', '').strip()
        if status:
            recruitment_invoices = recruitment_invoices.filter(status=status)
            general_invoices = general_invoices.filter(status=status)
        
        # Add type filtering
        invoice_type = request.GET.get('type', '').strip()
        if invoice_type == 'recruitment':
            general_invoices = GeneralInvoice.objects.none()
        elif invoice_type == 'general':
            recruitment_invoices = Invoice.objects.none()
        
        # Combine them for display - SIMPLIFIED approach
        all_invoices = []
        
        # Add recruitment invoices with type indicator
        for inv in recruitment_invoices:
            if inv.id and inv.placement:  # Safety checks
                try:
                    client_name = inv.placement.client.name if inv.placement.client else 'Unknown Client'
                    candidate_name = inv.placement.candidate.name if inv.placement.candidate else 'Unknown Candidate'
                    # SIMPLIFIED: Just use direct URL construction
                    detail_url = f'/invoicing/invoices/{inv.id}/'
                except Exception as e:
                    client_name = 'Unknown Client'
                    candidate_name = 'Unknown Candidate'
                    detail_url = f'/invoicing/invoices/{inv.id}/'
                    
                all_invoices.append({
                    'invoice': inv,
                    'type': 'recruitment',
                    'client_name': client_name,
                    'candidate_name': candidate_name,
                    'detail_url': detail_url,
                    'type_display': 'Recruitment',
                    'type_icon': 'users',
                    'type_class': 'primary'
                })
        
        # Add general invoices with type indicator
        for inv in general_invoices:
            if inv.id:  # Safety checks
                try:
                    # SIMPLIFIED: Just use direct URL construction
                    detail_url = f'/invoicing/general-invoices/{inv.id}/'
                except Exception as e:
                    detail_url = f'/invoicing/general-invoices/{inv.id}/'
                    
                all_invoices.append({
                    'invoice': inv,
                    'type': 'general',
                    'client_name': inv.client_name or 'Unknown Client',
                    'candidate_name': None,
                    'detail_url': detail_url,
                    'type_display': 'General',
                    'type_icon': 'file-text',
                    'type_class': 'info'
                })
        
        # Sort by creation date (most recent first)
        all_invoices.sort(key=lambda x: x['invoice'].created_at, reverse=True)
        
        # Calculate statistics
        total_recruitment = recruitment_invoices.count()
        total_general = general_invoices.count()
        total_invoices = total_recruitment + total_general
        
        # Revenue calculations
        recruitment_revenue = sum([inv.total_amount for inv in recruitment_invoices if inv.status == 'paid'])
        general_revenue = sum([inv.total_amount for inv in general_invoices if inv.status == 'paid'])
        total_revenue = recruitment_revenue + general_revenue
        
        # Pending revenue
        pending_recruitment = sum([inv.total_amount for inv in recruitment_invoices if inv.status in ['draft', 'sent']])
        pending_general = sum([inv.total_amount for inv in general_invoices if inv.status in ['draft', 'sent']])
        pending_revenue = pending_recruitment + pending_general
        
        # Status counts
        draft_count = recruitment_invoices.filter(status='draft').count() + general_invoices.filter(status='draft').count()
        sent_count = recruitment_invoices.filter(status='sent').count() + general_invoices.filter(status='sent').count()
        paid_count = recruitment_invoices.filter(status='paid').count() + general_invoices.filter(status='paid').count()
        overdue_count = recruitment_invoices.filter(status='overdue').count() + general_invoices.filter(status='overdue').count()
        
        context = {
            'invoices': all_invoices,
            'status_choices': Invoice.STATUS_CHOICES,
            'recruitment_count': total_recruitment,
            'general_count': total_general,
            'total_count': total_invoices,
            'current_search': search,
            'current_status': status,
            'current_type': invoice_type,
            'today': timezone.now().date(),
            'stats': {
                'total_revenue': total_revenue,
                'pending_revenue': pending_revenue,
                'draft_count': draft_count,
                'sent_count': sent_count,
                'paid_count': paid_count,
                'overdue_count': overdue_count,
            },
        }
        
        # FIXED: Use correct template path based on your structure
        return render(request, 'invoicing/Invoicing/invoice_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading invoices: {str(e)}')
        return render(request, 'invoicing/Invoicing/invoice_list.html', {
            'invoices': [],
            'status_choices': Invoice.STATUS_CHOICES,
            'recruitment_count': 0,
            'general_count': 0,
            'total_count': 0,
            'current_search': '',
            'current_status': '',
            'current_type': '',
            'today': timezone.now().date(),
            'stats': {
                'total_revenue': 0,
                'pending_revenue': 0,
                'draft_count': 0,
                'sent_count': 0,
                'paid_count': 0,
                'overdue_count': 0,
            },
        })
    

@login_required
def general_invoice_create(request):
    """Create new general invoice with auto PDF generation"""
    if request.method == 'POST':
        try:
            # Get form data
            client_name = request.POST.get('client_name')
            client_email = request.POST.get('client_email')
            client_phone = request.POST.get('client_phone', '')
            client_address = request.POST.get('client_address')
            service_description = request.POST.get('service_description')
            amount = Decimal(str(request.POST.get('amount')))
            tax_rate = Decimal(str(request.POST.get('tax_rate', '18.0')))
            due_days = int(request.POST.get('due_days', 30))
            
            # Validate required fields
            if not all([client_name, client_email, client_address, service_description, amount]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'invoicing/General/general_invoice_form.html', {'form_action': 'create'})
            
            # Create general invoice
            invoice = GeneralInvoice.objects.create(
                client_name=client_name,
                client_email=client_email,
                client_phone=client_phone,
                client_address=client_address,
                service_description=service_description,
                amount=amount,
                tax_rate=tax_rate,
                status='draft',
                created_by=request.user
            )
            
            # Set due date
            if due_days > 0:
                from datetime import timedelta
                invoice.due_date = invoice.issue_date + timedelta(days=due_days)
                invoice.save()
            
            # AUTOMATICALLY GENERATE AND SAVE PDF
            try:
                pdf_content = generate_general_invoice_pdf(invoice)
                invoice.save_generated_pdf(pdf_content)
                pdf_generated = True
            except Exception as pdf_error:
                print(f"PDF generation failed: {pdf_error}")
                pdf_generated = False
            
            # Success message
            success_msg = f"General invoice {invoice.invoice_number} created successfully!"
            if pdf_generated:
                success_msg += " PDF has been generated and saved."
            
            messages.success(request, success_msg)
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice_id': invoice.id,
                    'invoice_number': str(invoice.invoice_number),
                    'redirect_url': f'/invoicing/general-invoices/{invoice.id}/',
                    'pdf_generated': pdf_generated
                })
            
            return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
            
        except Exception as e:
            error_msg = f'Error creating general invoice: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            
            messages.error(request, error_msg)
    
    return render(request, 'invoicing/General/general_invoice_form.html', {'form_action': 'create'})
@login_required

def general_invoice_detail(request, invoice_id):
    """View general invoice details"""
    try:
        invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
        
        # Handle POST requests for actions
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'mark_paid':
                # Handle mark as paid
                old_status = invoice.status
                payment_date = request.POST.get('payment_date')
                payment_notes = request.POST.get('payment_notes', '')
                
                invoice.status = 'paid'
                if payment_date:
                    from datetime import datetime
                    invoice.payment_received_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                else:
                    invoice.payment_received_date = timezone.now().date()
                
                invoice.payment_notes = payment_notes
                invoice.save()
                
                messages.success(request, f'✅ General invoice {invoice.invoice_number} marked as paid successfully!')
                return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
        
        # Calculate tax amount - FIXED: Handle Decimal properly
        if invoice.amount and invoice.tax_rate:
            amount = Decimal(str(invoice.amount))
            tax_rate = Decimal(str(invoice.tax_rate))
            tax_amount = (amount * tax_rate) / Decimal('100')
        else:
            tax_amount = Decimal('0')
        
        # Convert back to float for template display
        tax_amount = float(tax_amount)
        
        context = {
            'invoice': invoice,
            'tax_amount': tax_amount,
        }
        
        return render(request, 'invoicing/General/general_invoice_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'❌ Error loading general invoice: {str(e)}')
        return redirect('invoicing:invoice_list')

@login_required
def generate_general_invoice_pdf(invoice):
    """Generate PDF content for general invoice"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=0.8*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.8*inch,
        rightMargin=0.8*inch
    )
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Calculate tax amount
    tax_amount = Decimal('0')
    if invoice.amount and invoice.tax_rate:
        tax_amount = (invoice.amount * invoice.tax_rate) / Decimal('100')
    
    # Title
    title = Paragraph("GENERAL INVOICE", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 30))
    
    # Invoice info table
    invoice_info_data = [
        ['Invoice Number:', str(invoice.invoice_number), 'Issue Date:', invoice.issue_date.strftime('%B %d, %Y')],
        ['Status:', invoice.get_status_display(), 'Due Date:', invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Not Set'],
    ]
    
    invoice_info_table = Table(invoice_info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    invoice_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(invoice_info_table)
    elements.append(Spacer(1, 30))
    
    # Bill To and Service Provider - FIXED: Remove any reference to invoice.user
    bill_service_data = [
        ['BILL TO:', 'SERVICE PROVIDER:'],
        [
            f"{invoice.client_name}\n{invoice.client_address}\nEmail: {invoice.client_email}\nPhone: {invoice.client_phone or 'N/A'}",
            "Your Company Name\nYour Address\nYour City, State, ZIP\nEmail: your-email@company.com\nPhone: Your Phone Number"
        ]
    ]
    
    bill_service_table = Table(bill_service_data, colWidths=[3.5*inch, 3.5*inch])
    bill_service_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
    ]))
    
    elements.append(bill_service_table)
    elements.append(Spacer(1, 30))
    
    # Service Details
    service_header = Paragraph("<b>SERVICE DETAILS</b>", styles['Heading2'])
    elements.append(service_header)
    elements.append(Spacer(1, 10))
    
    # FIXED: Use safe string handling for service description
    service_description = str(invoice.service_description) if invoice.service_description else "No description provided"
    service_details = f"""
    <para>
    <b>Service Description:</b><br/>
    {service_description}
    </para>
    """
    elements.append(Paragraph(service_details, styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Invoice Items Table
    table_data = [
        ['Description', 'Amount (₹)'],
        [service_description, f"{float(invoice.amount):,.2f}"],
    ]
    
    if tax_amount > 0:
        table_data.append([f"Tax ({float(invoice.tax_rate)}%)", f"{float(tax_amount):,.2f}"])
    
    table_data.append(['', ''])
    table_data.append(['TOTAL AMOUNT', f"₹{float(invoice.total_amount):,.2f}"])
    
    invoice_table = Table(table_data, colWidths=[4.5*inch, 2.5*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -3), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -3), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(invoice_table)
    elements.append(Spacer(1, 40))
    
    # Payment Instructions
    payment_instructions = f"""
    <para>
    <b>PAYMENT INSTRUCTIONS:</b><br/>
    Please process payment by {invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else '30 days from issue date'}.
    Reference invoice number {invoice.invoice_number} in your payment.
    </para>
    """
    elements.append(Paragraph(payment_instructions, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = """
    <para align="center">
    <b>Thank you for your business!</b><br/>
    For questions regarding this invoice, please contact us immediately.
    </para>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data and close buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data


@login_required
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


@login_required
def general_invoice_download_pdf(request, invoice_id):
    """Download general invoice PDF"""
    try:
        invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
        
        # Check if PDF exists
        if not invoice.pdf_file:
            # Generate PDF if not exists
            try:
                pdf_content = generate_general_invoice_pdf(invoice)
                invoice.save_generated_pdf(pdf_content)
            except Exception as e:
                messages.error(request, f'Error generating PDF: {str(e)}')
                return redirect('invoicing:general_invoice_detail', invoice_id=invoice_id)
        
        # Create response
        try:
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="General_Invoice_{invoice.invoice_number}.pdf"'
            
            # Read file content
            invoice.pdf_file.open('rb')
            response.write(invoice.pdf_file.read())
            invoice.pdf_file.close()
            
            return response
            
        except Exception as e:
            messages.error(request, f'Error opening PDF file: {str(e)}')
            return redirect('invoicing:general_invoice_detail', invoice_id=invoice_id)
        
    except Exception as e:
        messages.error(request, f'Error downloading PDF: {str(e)}')
        return redirect('invoicing:general_invoice_detail', invoice_id=invoice_id)

@login_required
def general_invoice_upload_pdf(request, invoice_id):
    """Upload custom PDF to replace generated one"""
    try:
        invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
        
        if request.method == 'POST' and request.FILES.get('pdf_file'):
            uploaded_file = request.FILES['pdf_file']
            
            # Validate file type
            if not uploaded_file.name.lower().endswith('.pdf'):
                messages.error(request, 'Please upload a PDF file only.')
                return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
            
            # Replace PDF
            invoice.replace_pdf(uploaded_file, request.user)
            
            messages.success(request, f'Custom PDF uploaded successfully for invoice {invoice.invoice_number}!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'PDF uploaded successfully',
                    'pdf_url': invoice.pdf_file.url if invoice.pdf_file else None
                })
        
        return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
        
    except Exception as e:
        error_msg = f'Error uploading PDF: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        
        messages.error(request, error_msg)
        return redirect('invoicing:general_invoice_detail', invoice_id=invoice_id)



@login_required
def client_detail(request, client_id):
    """View client details"""
    client = get_object_or_404(Client, id=client_id)
    
    # Get client's invoices
    recruitment_invoices = Invoice.objects.filter(placement__client=client)
    general_invoices = GeneralInvoice.objects.filter(client_name__icontains=client.name)
    
    # Calculate statistics
    total_invoices = recruitment_invoices.count() + general_invoices.count()
    total_amount = sum([inv.total_amount for inv in recruitment_invoices]) + sum([inv.total_amount for inv in general_invoices])
    paid_invoices = recruitment_invoices.filter(status='paid').count() + general_invoices.filter(status='paid').count()
    
    context = {
        'client': client,
        'recruitment_invoices': recruitment_invoices,
        'general_invoices': general_invoices,
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'paid_invoices': paid_invoices,
    }
    return render(request, 'invoicing/Client/client_detail.html', context)

@login_required
def client_edit(request, client_id):
    """Edit client"""
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        # Update client fields
        client.name = request.POST.get('name', client.name)
        client.contact_person = request.POST.get('contact_person', client.contact_person)
        client.email = request.POST.get('email', client.email)
        client.phone = request.POST.get('phone', client.phone)
        client.address = request.POST.get('address', client.address)
        client.is_active = request.POST.get('is_active') == 'on'
        
        try:
            client.save()
            messages.success(request, f'Client "{client.name}" updated successfully.')
            return redirect('invoicing:client_detail', client_id=client.id)
        except Exception as e:
            messages.error(request, f'Error updating client: {str(e)}')
    
    context = {
        'client': client,
        'form_action': 'edit',
    }
    return render(request, 'invoicing/Client/client_form.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def client_delete(request, client_id):
    """Delete client"""
    client = get_object_or_404(Client, id=client_id)
    
    try:
        # Check if client has any placements (which could have invoices)
        has_placements = Placement.objects.filter(client=client).exists()
        
        if has_placements:
            return JsonResponse({
                'success': False, 
                'message': 'Cannot delete client with existing placements/invoices. Please delete placements first.'
            })
        
        # Check for general invoices by client name
        has_general_invoices = GeneralInvoice.objects.filter(client_name__icontains=client.name).exists()
        
        if has_general_invoices:
            return JsonResponse({
                'success': False, 
                'message': 'Cannot delete client with existing general invoices. Please delete invoices first.'
            })
        
        client_name = client.name
        client.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Client "{client_name}" deleted successfully.'
        })
            
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error deleting client: {str(e)}'
        })

@login_required
def general_invoice_send_email(request, invoice_id):
    """Send general invoice via email"""
    invoice = get_object_or_404(GeneralInvoice, id=invoice_id)
    
    if request.method == 'POST':
        try:
            # Get email details from form or use defaults
            recipient_email = request.POST.get('recipient_email', invoice.client_email)
            subject = request.POST.get('subject', f'Invoice {invoice.invoice_number} from {settings.DEFAULT_FROM_EMAIL}')
            custom_message = request.POST.get('custom_message', '')
            
            # Prepare context for email template
            context = {
                'invoice': invoice,
                'custom_message': custom_message,
                'company_name': getattr(settings, 'COMPANY_NAME', 'Your Company'),
                'company_address': getattr(settings, 'COMPANY_ADDRESS', ''),
                'company_phone': getattr(settings, 'COMPANY_PHONE', ''),
                'company_email': getattr(settings, 'COMPANY_EMAIL', settings.DEFAULT_FROM_EMAIL),
                'website_url': request.build_absolute_uri('/'),
            }
            
            # Render email templates
            html_content = render_to_string('invoicing/emails/general_invoice_email.html', context)
            text_content = render_to_string('invoicing/emails/general_invoice_email.txt', context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            # Update invoice status
            if invoice.status == 'draft':
                invoice.status = 'sent'
                invoice.save()
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Invoice sent successfully to {recipient_email}'
                })
            
            messages.success(request, f'Invoice sent successfully to {recipient_email}')
            return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
            
        except Exception as e:
            error_message = f'Error sending invoice: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            
            messages.error(request, error_message)
            return redirect('invoicing:general_invoice_detail', invoice_id=invoice.id)
    
    # GET request - show email form
    context = {
        'invoice': invoice,
        'default_subject': f'Invoice {invoice.invoice_number} from {getattr(settings, "COMPANY_NAME", "Your Company")}',
        'default_recipient': invoice.client_email,
    }
    return render(request, 'invoicing/General/general_invoice_send_email.html', context)



@login_required
def candidate_list(request):
    """List all candidates"""
    candidates = Candidate.objects.all().order_by('-created_at')
    
    # Process skills for each candidate
    for candidate in candidates:
        if candidate.skills:
            candidate.skills_list = [skill.strip() for skill in candidate.skills.split(',') if skill.strip()]
        else:
            candidate.skills_list = []
    
    # Calculate statistics
    stats = {
        'total': candidates.count(),
        'active': candidates.filter(status='active').count(),
        'placed': candidates.filter(status='placed').count(),
        'inactive': candidates.filter(status='inactive').count(),
    }
    
    context = {
        'candidates': candidates,
        'stats': stats,
    }
    return render(request, 'invoicing/Candidate/candidate_list.html', context)

@login_required
def candidate_create(request):
    """Create new candidate"""
    if request.method == 'POST':
        try:
            # Validate required fields
            name = request.POST.get('name')
            if not name:
                error_msg = '❌ Candidate name is required.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return render(request, 'invoicing/Candidate/candidate_form.html', {'form_action': 'create'})
            
            candidate = Candidate.objects.create(
                name=name,
                email=request.POST.get('email'),
                phone=request.POST.get('phone', ''),
                current_company=request.POST.get('current_company', ''),
                current_position=request.POST.get('current_position', ''),
                experience_years=int(request.POST.get('experience_years', 0)),
                skills=request.POST.get('skills', ''),
                linkedin_profile=request.POST.get('linkedin_profile', ''),
                expected_salary=float(request.POST.get('expected_salary')) if request.POST.get('expected_salary') else None,
                notice_period_days=int(request.POST.get('notice_period_days', 30)),
                preferred_location=request.POST.get('preferred_location', ''),
                availability_date=request.POST.get('availability_date') if request.POST.get('availability_date') else None,
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            # Handle AJAX requests (from modal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'id': candidate.id, 
                    'name': candidate.name,
                    'position': candidate.current_position or 'No Position',
                    'experience': f'{candidate.experience_years} yrs',
                    'message': f'Candidate "{candidate.name}" created successfully!'
                })
            
            # Regular form submission
            messages.success(request, f'✅ Candidate "{candidate.name}" has been added successfully!')
            return redirect('invoicing:candidate_detail', candidate_id=candidate.id)
            
        except ValueError as e:
            error_msg = f'❌ Invalid data provided: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f'❌ Error creating candidate: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
    
    return render(request, 'invoicing/Candidate/candidate_form.html', {'form_action': 'create'})

@login_required
def candidate_detail(request, candidate_id):
    """View candidate details"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    # Process skills
    if candidate.skills:
        candidate.skills_list = [skill.strip() for skill in candidate.skills.split(',') if skill.strip()]
    else:
        candidate.skills_list = []
    
    # Get candidate's placements
    placements = Placement.objects.filter(candidate=candidate).order_by('-created_at')
    
    # Calculate statistics
    total_placements = placements.count()
    successful_placements = placements.filter(status__in=['completed', 'invoiced']).count()
    total_revenue = sum([p.placement_fee for p in placements if p.status in ['completed', 'invoiced']])
    
    context = {
        'candidate': candidate,
        'placements': placements,
        'total_placements': total_placements,
        'successful_placements': successful_placements,
        'total_revenue': total_revenue,
    }
    return render(request, 'invoicing/Candidate/candidate_detail.html', context)

@login_required
def candidate_edit(request, candidate_id):
    """Edit candidate"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    if request.method == 'POST':
        try:
            candidate.name = request.POST.get('name', candidate.name)
            candidate.email = request.POST.get('email', candidate.email)
            candidate.phone = request.POST.get('phone', candidate.phone)
            candidate.current_company = request.POST.get('current_company', candidate.current_company)
            candidate.current_position = request.POST.get('current_position', candidate.current_position)
            candidate.experience_years = int(request.POST.get('experience_years', candidate.experience_years))
            candidate.skills = request.POST.get('skills', candidate.skills)
            candidate.linkedin_profile = request.POST.get('linkedin_profile', candidate.linkedin_profile)
            candidate.expected_salary = float(request.POST.get('expected_salary')) if request.POST.get('expected_salary') else candidate.expected_salary
            candidate.notice_period_days = int(request.POST.get('notice_period_days', candidate.notice_period_days))
            candidate.preferred_location = request.POST.get('preferred_location', candidate.preferred_location)
            candidate.availability_date = request.POST.get('availability_date') if request.POST.get('availability_date') else candidate.availability_date
            candidate.status = request.POST.get('status', candidate.status)
            candidate.notes = request.POST.get('notes', candidate.notes)
            candidate.save()
            
            messages.success(request, f'Candidate "{candidate.name}" updated successfully.')
            return redirect('invoicing:candidate_detail', candidate_id=candidate.id)
            
        except Exception as e:
            messages.error(request, f'Error updating candidate: {str(e)}')
    
    context = {
        'candidate': candidate,
        'form_action': 'edit',
    }
    return render(request, 'invoicing/Candidate/candidate_form.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def candidate_delete(request, candidate_id):
    """Delete candidate"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    try:
        # Check if candidate has any placements
        has_placements = Placement.objects.filter(candidate=candidate).exists()
        
        if has_placements:
            return JsonResponse({
                'success': False, 
                'message': 'Cannot delete candidate with existing placements. Please delete placements first.'
            })
        
        candidate_name = candidate.name
        candidate.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Candidate "{candidate_name}" deleted successfully.'
        })
            
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error deleting candidate: {str(e)}'
        })

@login_required
def placement_create(request):
    """Create new placement with candidate prefill"""
    # Get candidate ID from URL parameter for prefilling
    candidate_id = request.GET.get('candidate')
    selected_candidate = None
    
    if candidate_id:
        try:
            selected_candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            messages.warning(request, 'Selected candidate not found.')
    
    if request.method == 'POST':
        try:
            # Get form data
            candidate_id = request.POST.get('candidate')
            client_id = request.POST.get('client')
            position = request.POST.get('position')
            joining_date = request.POST.get('joining_date')
            notice_period_days = int(request.POST.get('notice_period_days', 90))
            placement_fee = float(request.POST.get('placement_fee'))
            offered_salary = request.POST.get('offered_salary')
            placement_type = request.POST.get('placement_type', 'permanent')
            create_invoice_now = request.POST.get('create_invoice_now') == 'on'
            
            # Validate required fields
            if not all([candidate_id, client_id, position, joining_date, placement_fee]):
                messages.error(request, '❌ Please fill in all required fields.')
                context = {
                    'candidates': Candidate.objects.filter(status='active').order_by('name'),
                    'clients': Client.objects.filter(is_active=True).order_by('name'),
                    'selected_candidate': selected_candidate,
                }
                return render(request, 'invoicing/placements/placement_create.html', context)
            
            # Get objects
            candidate = get_object_or_404(Candidate, id=candidate_id)
            client = get_object_or_404(Client, id=client_id)
            
            # Parse joining date
            from datetime import datetime
            joining_date_obj = datetime.strptime(joining_date, '%Y-%m-%d').date()
            
            # Create placement with 'joined' status so it can be eligible
            placement = Placement.objects.create(
                candidate=candidate,
                client=client,
                position=position,
                joining_date=joining_date_obj,
                notice_period_days=notice_period_days,
                placement_fee=placement_fee,
                offered_salary=float(offered_salary) if offered_salary else None,
                placement_type=placement_type,
                status='joined',  # Set to 'joined' so it can be eligible for invoice
                created_by=request.user
            )
            
            # Update candidate status to placed
            candidate.status = 'placed'
            candidate.save()
            
            # Create invoice if requested OR if eligible
            if create_invoice_now or placement.is_invoice_eligible:
                invoice = Invoice.objects.create(
                    placement=placement,
                    amount=placement_fee,
                    tax_rate=18.0,
                    status='draft'
                )
                # Update placement status to invoiced
                placement.status = 'invoiced'
                placement.save()
                
                messages.success(request, f'✅ Placement created successfully! Invoice {invoice.invoice_number} has been generated.')
                return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
            else:
                eligible_date = placement.invoice_eligible_date.strftime('%B %d, %Y')
                messages.success(request, f'✅ Placement for {candidate.name} at {client.name} created successfully! Invoice will be eligible on {eligible_date}.')
                return redirect('invoicing:placement_list')
                
        except ValueError as e:
            messages.error(request, f'❌ Invalid data provided: {str(e)}')
        except Exception as e:
            messages.error(request, f'❌ Error creating placement: {str(e)}')
    
    # GET request - show form
    context = {
        'candidates': Candidate.objects.filter(status='active').order_by('name'),
        'clients': Client.objects.filter(is_active=True).order_by('name'),
        'selected_candidate': selected_candidate,
    }
    return render(request, 'invoicing/placements/placement_create.html', context)

@login_required
def update_invoice_status(request, invoice_id):
    """Update invoice status"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if request.method == 'POST':
            old_status = invoice.status
            new_status = request.POST.get('new_status')
            notes = request.POST.get('notes', '')
            
            if new_status and new_status in dict(Invoice.STATUS_CHOICES):
                invoice.status = new_status
                invoice.save()
                
                # Create history entry
                InvoiceHistory.objects.create(
                    invoice=invoice,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    notes=notes
                )
                
                messages.success(request, f'✅ Invoice status updated to {invoice.get_status_display()}')
            else:
                messages.error(request, '❌ Invalid status selected.')
        
        return redirect('invoicing:invoice_detail', invoice_id=invoice.id)
        
    except Exception as e:
        messages.error(request, f'❌ Error updating status: {str(e)}')
        return redirect('invoicing:invoice_detail', invoice_id=invoice_id)