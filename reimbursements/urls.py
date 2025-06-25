from django.urls import path
from .views import mark_reimbursement_done, reimbursement_detail, reimbursement_list, reimbursement_success, upload_reimbursement


from .views_api import (
    ReimbursementUploadAPI,
    ReimbursementListAPI,
    ReimbursementDetailAPI,
    MarkReimbursementDoneAPI,
)

urlpatterns = [
    path('list/', reimbursement_list, name='reimbursement_list'),
    path('mark_done/<int:pk>/', mark_reimbursement_done, name='mark_done'),
    path('success/', reimbursement_success, name='reimbursement_success'),
    path('view/<int:pk>/', reimbursement_detail, name='reimbursement_detail'),
    path('upload/', upload_reimbursement, name='upload_reimbursement'),

    
    path('api/upload/', ReimbursementUploadAPI.as_view(), name='api_upload_reimbursement'),
    path('api/all/', ReimbursementListAPI.as_view(), name='api_all_reimbursements'),
    path('api/<int:pk>/', ReimbursementDetailAPI.as_view(), name='api_reimbursement_detail'),
    path('api/<int:pk>/done/', MarkReimbursementDoneAPI.as_view(), name='api_reimbursement_done'),
]
