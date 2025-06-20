from django import forms
from django.utils import timezone
from .models import Client, GeneralInvoice, Placement, Invoice, InvoiceNotification
from recruitment.models import Candidate

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'contact_person', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PlacementForm(forms.ModelForm):
    class Meta:
        model = Placement
        fields = ['candidate', 'client', 'position', 'joining_date', 'notice_period_days', 'placement_fee']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notice_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'placement_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.instance.created_by = user

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['amount', 'tax_rate', 'due_date']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class EmailForm(forms.Form):
    subject = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 10})
    )

class GeneralInvoiceForm(forms.ModelForm):
    class Meta:
        model = GeneralInvoice
        fields = [
            'client_name', 'client_email', 'client_phone', 'client_address',
            'service_description', 'amount', 'tax_rate', 'status',
            'email_subject', 'email_body'
        ]
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'oh-form__input', 'placeholder': 'Client Name'}),
            'client_email': forms.EmailInput(attrs={'class': 'oh-form__input', 'placeholder': 'client@example.com'}),
            'client_phone': forms.TextInput(attrs={'class': 'oh-form__input', 'placeholder': '+1234567890'}),
            'client_address': forms.Textarea(attrs={'class': 'oh-form__textarea', 'rows': 3, 'placeholder': 'Client Address'}),
            'service_description': forms.Textarea(attrs={'class': 'oh-form__textarea', 'rows': 4, 'placeholder': 'Description of services provided'}),
            'amount': forms.NumberInput(attrs={'class': 'oh-form__input', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'oh-form__input', 'step': '0.01', 'min': '0', 'max': '100'}),
            'status': forms.Select(attrs={'class': 'oh-form__input'}),
            'email_subject': forms.TextInput(attrs={'class': 'oh-form__input', 'placeholder': 'Invoice email subject'}),
            'email_body': forms.Textarea(attrs={'class': 'oh-form__textarea', 'rows': 6, 'placeholder': 'Email message body'}),
        }