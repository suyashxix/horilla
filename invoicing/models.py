from django.db import models
from django.utils import timezone
from datetime import timedelta
from recruitment.models import Candidate
from base.models import Company
from django.contrib.auth.models import User
# Create your models here.

class Client(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20,blank=True)
    contact_person = models.CharField(max_length=255)
    address= models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
class Placement(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    position = models.CharField(max_length=255)
    joining_date= models.DateField()
    notice_period_days=models.PositiveIntegerField(default=90, help_text="No of days till invoice is generated")
    placement_fee = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active=models.BooleanField(default=True)
    @property
    def invoice_eligible_date(self):
        if self.joining_date:
            return self.joining_date + timedelta(days=self.notice_period_days)
        
    @property
    def is_invoice_eligible(self):
        return self.invoice_eligible_date <= timezone.now().date()
    @property
    def days_until_eligible_invoice(self):
        if self.invoice_eligible_date:
            return (self.invoice_eligible_date - timezone.now().date()).days
    
    def __str__(self):
        return f'{self.candidate} at {self.client}'
    
    class Meta:
        ordering=['-created_at']
class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft','Draft'),
        ('paid','Paid'),
        ('cancelled','Cancelled'),
        ('overdue','Overdue'),
        ('sent','Sent'),
        ("ready_to_send","Ready to Send")

    )
    placement = models.OneToOneField(Placement, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    issue_date = models.DateField(auto_now_add=True)
    due_date= models.DateField(blank=True, null=True)

    status= models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft"
                             )
    pdf_file = models.FileField(upload_to='invoices/pdfs/', blank=True, null=True)

    #Email 
    email_subject = models.CharField(max_length=255, blank=True)
    email_body = models.TextField(blank=True)
    sent_at= models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,blank=True)
    #Paying tracked
    payment_received_date = models.DateField(null=True, blank=True)
    payment_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            today = timezone.now().date()
            today_invoices = Invoice.objects.filter(
                issue_date=today
            ).count()
            self.invoice_number= f"INV-{today.strftime('%Y%m%d')}-{today_invoices + 1:03d}"

        if self.amount and self.tax_rate:
            tax_amount=(self.amount *self.tax_rate)/100
            self.total_amount = tax_amount+self.amount
        
        if not self.due_date and self.issue_date:
            self.due_date = self.issue_date + timedelta(days=30)
        
        super().save(*args, **kwargs)
    @property 
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.placement.client.name}"
    class Meta:
        ordering = ['-created_at']

class InvoiceNotification(models.Model):
    NOTIFICATION_TYPE=(
        ('eligible', "Eligible for Invoicing"),
        ('overdue', "Invoice Overdue"),
        ('sent', "Invoice Sent"),
        ('paid', "Invoice Paid"),
    )  
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    message= models.TextField()
    is_read= models.BooleanField(default=False)
    created_at= models.DateTimeField(auto_now_add=True)
    notified_user= models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.placement}"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ["placement", "notification_type", 'notified_user']

class InvoiceHistory(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.invoice.invoice_number}: {self.old_status} → {self.new_status}"
    
    class Meta:
        ordering = ['-changed_at']