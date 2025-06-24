from django import forms
from .models import Reimbursement

class ReimbursementForm(forms.ModelForm):
    class Meta:
        model = Reimbursement
        fields = ['image', 'note']
