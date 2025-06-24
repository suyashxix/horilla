from django.urls import path
from .views import upload_reimbursement
from .views_api import ReimbursementUploadAPI

urlpatterns = [
    path('upload/', upload_reimbursement, name='upload_reimbursement'),
    path('api/upload/', ReimbursementUploadAPI.as_view(), name='api_upload_reimbursement'),
]
