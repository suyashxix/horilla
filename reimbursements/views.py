from django.shortcuts import render, redirect
from .forms import ReimbursementForm
 
from django.views.decorators.csrf import csrf_exempt
from .models import Reimbursement


def upload_reimbursement(request):
    if request.method == 'POST':
        form = ReimbursementForm(request.POST, request.FILES)
        if form.is_valid():
            reimbursement = form.save(commit=False)
            amount, vendor = None, None
            reimbursement.amount = amount
            reimbursement.vendor = vendor
            reimbursement.save()
            return redirect('reimbursement_success')
    else:
        form = ReimbursementForm()
    return render(request, 'reimbursement/upload.html', {'form': form})



def reimbursement_list(request):
    reimbursements = Reimbursement.objects.all().order_by('-uploaded_at')
    return render(request, 'reimbursement/list.html', {'reimbursements': reimbursements})

@csrf_exempt
def mark_reimbursement_done(request, pk):
    if request.method == 'POST':
        try:
            reimbursement = Reimbursement.objects.get(pk=pk)
            reimbursement.status = 'done'
            reimbursement.save()
        except Reimbursement.DoesNotExist:
            pass
    return redirect('reimbursement_list')


def reimbursement_success(request):
    return render(request, 'reimbursement/success.html')


def reimbursement_detail(request, pk):
    try:
        reimbursement = Reimbursement.objects.get(pk=pk)
    except Reimbursement.DoesNotExist:
        return redirect('reimbursement_list')
    return render(request, 'reimbursement/detail.html', {'reimbursement': reimbursement})




