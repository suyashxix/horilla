from django.db import models


class Reimbursement(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
    ]

    image = models.ImageField(upload_to='invoices/')
    note = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
