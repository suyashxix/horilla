from decimal import Decimal
from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from base.models import Company
from django.contrib.auth.models import User
from django.core.files.base import ContentFile

class Client(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    contact_person = models.CharField(max_length=255)
    address = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        permissions = [
            ("manage_clients", "Can manage clients"),
            ("view_client_reports", "Can view client reports"),
        ]

class Candidate(models.Model):
    """Model for candidates placed at other companies"""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    current_company = models.CharField(max_length=200, blank=True, null=True)
    current_position = models.CharField(max_length=200, blank=True, null=True)
    experience_years = models.PositiveIntegerField(default=0)
    skills = models.TextField(blank=True, null=True)
    resume = models.FileField(upload_to='invoicing/candidates/resumes/', blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notice_period_days = models.PositiveIntegerField(default=30)
    preferred_location = models.CharField(max_length=200, blank=True, null=True)
    availability_date = models.DateField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('placed', 'Placed'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoicing_candidates')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'invoicing_candidate'
        verbose_name = 'Invoicing Candidate'
        verbose_name_plural = 'Invoicing Candidates'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.current_position or 'No Position'}"
    
    @property
    def is_available(self):
        return self.status == 'active'
    
    @property
    def experience_level(self):
        if self.experience_years <= 2:
            return 'Junior'
        elif self.experience_years <= 5:
            return 'Mid-level'
        elif self.experience_years <= 10:
            return 'Senior'
        else:
            return 'Expert'
class Placement(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='placements')
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='placements')
    position = models.CharField(max_length=200)
    joining_date = models.DateField()
    notice_period_days = models.PositiveIntegerField(default=90)
    placement_fee = models.DecimalField(max_digits=10, decimal_places=2)
    offered_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    placement_type = models.CharField(
        max_length=20,
        choices=[
            ('permanent', 'Permanent'),
            ('contract', 'Contract'),
            ('temp_to_perm', 'Temp to Permanent'),
        ],
        default='permanent'
    )
    
    STATUS_CHOICES = [
        ('offered', 'Offer Made'),
        ('accepted', 'Offer Accepted'),
        ('joined', 'Candidate Joined'),
        ('eligible_for_invoice', 'Eligible for Invoice'),
        ('invoiced', 'Invoiced'),
        ('completed', 'Placement Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offered')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoicing_placements')
    
    class Meta:
        db_table = 'invoicing_placement'
        verbose_name = 'Placement'
        verbose_name_plural = 'Placements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.candidate.name} at {self.client.name} - {self.position}"
    
    @property
    def invoice_eligible_date(self):
        """Calculate when invoice becomes eligible"""
        return self.joining_date + timedelta(days=self.notice_period_days)
    
    @property
    def is_invoice_eligible(self):
        """Check if placement is eligible for invoice generation"""
        today = date.today()
        eligible_date = self.invoice_eligible_date
        return today >= eligible_date and self.status in ['joined', 'eligible_for_invoice']
    
    @property
    def days_until_eligible_invoice(self):
        """Days remaining until invoice eligible - returns integer"""
        if self.is_invoice_eligible:
            return 0
        
        today = date.today()
        eligible_date = self.invoice_eligible_date
        days_diff = (eligible_date - today).days
        return max(0, days_diff)
    
    @property
    def days_until_eligible(self):
        """Alias for backward compatibility"""
        return self.days_until_eligible_invoice
    
    @property
    def has_invoice(self):
        """Check if placement already has an invoice"""
        return hasattr(self, 'invoice') and self.invoice is not None
    
    def save(self, *args, **kwargs):
        """Override save to update status based on dates"""
        super().save(*args, **kwargs)
        
        # Auto-update status if eligible for invoice
        if self.is_invoice_eligible and self.status == 'joined':
            self.status = 'eligible_for_invoice'
            super().save(update_fields=['status'])

def invoice_pdf_upload_path(instance, filename):
    """Generate upload path for invoice PDFs"""
    return f'invoices/{instance.created_at.strftime("%Y/%m")}/invoice_{instance.invoice_number}_{filename}'

class Invoice(models.Model):
    placement = models.OneToOneField('Placement', on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    payment_received_date = models.DateField(blank=True, null=True)
    payment_notes = models.TextField(blank=True, null=True)
    
    # Email tracking
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_invoices')
    email_subject = models.CharField(max_length=200, blank=True, null=True)
    email_body = models.TextField(blank=True, null=True)
    
    # PDF storage fields
    pdf_file = models.FileField(
        upload_to=invoice_pdf_upload_path, 
        blank=True, 
        null=True,
        help_text="Generated or uploaded invoice PDF"
    )
    pdf_generated_at = models.DateTimeField(blank=True, null=True)
    pdf_uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='uploaded_invoice_pdfs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Generate invoice number if not exists
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate total amount
        if self.amount and self.tax_rate:
            tax_amount = (self.amount * self.tax_rate) / Decimal('100')
            self.total_amount = self.amount + tax_amount
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        from datetime import datetime
        year = datetime.now().year
        month = datetime.now().month
        
        # Get last invoice number for this month
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f'INV-{year}{month:02d}'
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            try:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        return f'INV-{year}{month:02d}-{new_num:04d}'
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    @property
    def tax_amount(self):
        if self.amount and self.tax_rate:
            return (self.amount * self.tax_rate) / Decimal('100')
        return Decimal('0')
    
    def save_generated_pdf(self, pdf_content, filename=None):
        """Save generated PDF content to the model"""
        if not filename:
            filename = f"invoice_{self.invoice_number}.pdf"
        
        # Delete old PDF if exists
        if self.pdf_file:
            try:
                self.pdf_file.delete(save=False)
            except Exception:
                pass
        
        # Create ContentFile and save
        pdf_file = ContentFile(pdf_content, name=filename)
        
        self.pdf_file = pdf_file
        self.pdf_generated_at = timezone.now()
        self.save()
        
        return self.pdf_file.url if self.pdf_file else None
    
    def replace_pdf(self, uploaded_file, user):
        """Replace existing PDF with uploaded one"""
        # Delete old PDF if exists
        if self.pdf_file:
            try:
                self.pdf_file.delete(save=False)
            except Exception:
                pass
        
        # Save new PDF
        self.pdf_file = uploaded_file
        self.pdf_uploaded_by = user
        self.save()
        
        return self.pdf_file.url

class InvoiceNotification(models.Model):
    NOTIFICATION_TYPE = (
        ('eligible', "Eligible for Invoicing"),
        ('overdue', "Invoice Overdue"),
        ('sent', "Invoice Sent"),
        ('paid', "Invoice Paid"),
    )
    
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notified_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.placement}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ["placement", "notification_type", 'notified_user']

def general_invoice_pdf_upload_path(instance, filename):
    """Generate upload path for general invoice PDFs"""
    return f'general_invoices/{instance.created_at.strftime("%Y/%m")}/invoice_{instance.invoice_number}_{filename}'

class InvoiceHistory(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.invoice.invoice_number}: {self.old_status} → {self.new_status}"  # FIXED: Removed the "14" character

    class Meta:
        ordering = ['-changed_at']
class GeneralInvoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=20, blank=True, null=True)
    client_address = models.TextField()
    
    service_description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    payment_received_date = models.DateField(blank=True, null=True)
    payment_notes = models.TextField(blank=True, null=True)
    
    # Email tracking
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_general_invoices')
    email_subject = models.CharField(max_length=200, blank=True, null=True)
    email_body = models.TextField(blank=True, null=True)
    
    # PDF storage fields
    pdf_file = models.FileField(
        upload_to=general_invoice_pdf_upload_path, 
        blank=True, 
        null=True,
        help_text="Generated or uploaded invoice PDF"
    )
    pdf_generated_at = models.DateTimeField(blank=True, null=True)
    pdf_uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='uploaded_general_invoice_pdfs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Generate invoice number if not exists
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate total amount
        if self.amount and self.tax_rate:
            tax_amount = (self.amount * self.tax_rate) / Decimal('100')
            self.total_amount = self.amount + tax_amount
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number for general invoices"""
        from datetime import datetime
        year = datetime.now().year
        month = datetime.now().month
        
        # Get last invoice number for this month
        last_invoice = GeneralInvoice.objects.filter(
            invoice_number__startswith=f'GEN-{year}{month:02d}'
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            try:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        return f'GEN-{year}{month:02d}-{new_num:04d}'
    
    def __str__(self):
        return f"General Invoice {self.invoice_number}"
    
    @property
    def tax_amount(self):
        if self.amount and self.tax_rate:
            return (self.amount * self.tax_rate) / Decimal('100')
        return Decimal('0')
    
    def save_generated_pdf(self, pdf_content, filename=None):
        """Save generated PDF content to the model"""
        if not filename:
            filename = f"general_invoice_{self.invoice_number}.pdf"
        
        # Delete old PDF if exists
        if self.pdf_file:
            try:
                self.pdf_file.delete(save=False)
            except Exception:
                pass
        
        # Create ContentFile and save
        pdf_file = ContentFile(pdf_content, name=filename)
        
        self.pdf_file = pdf_file
        self.pdf_generated_at = timezone.now()
        self.save()
        
        return self.pdf_file.url if self.pdf_file else None
    
    def replace_pdf(self, uploaded_file, user):
        """Replace existing PDF with uploaded one"""
        # Delete old PDF if exists
        if self.pdf_file:
            try:
                self.pdf_file.delete(save=False)
            except Exception:
                pass
        
        # Save new PDF
        self.pdf_file = uploaded_file
        self.pdf_uploaded_by = user
        self.save()
        
        return self.pdf_file.url

    class Meta:
        db_table = 'invoicing_general_invoice'
        verbose_name = 'General Invoice'
        verbose_name_plural = 'General Invoices'
        ordering = ['-created_at']


class GeneralInvoiceHistory(models.Model):
    invoice = models.ForeignKey(GeneralInvoice, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.invoice.invoice_number}: {self.old_status} → {self.new_status}"