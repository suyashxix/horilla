from django.shortcuts import render, redirect
from .forms import ReimbursementForm
from .ocr_utils import parse_invoice  # custom parsing logic

def upload_reimbursement(request):
    if request.method == 'POST':
        form = ReimbursementForm(request.POST, request.FILES)
        if form.is_valid():
            reimbursement = form.save(commit=False)
            amount, vendor = parse_invoice(reimbursement.image.path)
            reimbursement.amount = amount
            reimbursement.vendor = vendor
            reimbursement.save()
            return redirect('reimbursement_success')
    else:
        form = ReimbursementForm()
    return render(request, 'reimbursement/upload.html', {'form': form})

