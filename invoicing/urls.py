from django.urls import path, re_path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Traditional Django views
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/create/', views.client_create, name='client_create'),
    path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
    path('clients/<int:client_id>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:client_id>/delete/', views.client_delete, name='client_delete'),
    
    # Candidates (FIXED - removed external_candidate references)
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/create/', views.candidate_create, name='candidate_create'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:candidate_id>/edit/', views.candidate_edit, name='candidate_edit'),
    path('candidates/<int:candidate_id>/delete/', views.candidate_delete, name='candidate_delete'),
    
    # Placements
    path('placements/', views.placement_list, name='placement_list'),
    path('placements/create/', views.placement_create, name='placement_create'),
    
    # Recruitment Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/<int:placement_id>/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/send/', views.send_invoice_email, name='send_invoice'),
    path('invoices/<int:invoice_id>/mark-paid/', views.mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/<int:invoice_id>/send-email/', views.send_invoice_email, name='send_invoice_email'),

    # General Invoices
    path('general-invoices/create/', views.general_invoice_create, name='general_invoice_create'),
    path('general-invoices/<int:invoice_id>/', views.general_invoice_detail, name='general_invoice_detail'),
    path('general-invoices/<int:invoice_id>/mark-paid/', views.general_invoice_mark_paid, name='general_invoice_mark_paid'),
    path('general-invoices/<int:invoice_id>/send-email/', views.general_invoice_send_email, name='general_invoice_send_email'),
    #General PDF
    path('general-invoices/<int:invoice_id>/download-pdf/', views.general_invoice_download_pdf, name='general_invoice_download_pdf'),
    path('general-invoices/<int:invoice_id>/upload-pdf/', views.general_invoice_upload_pdf, name='general_invoice_upload_pdf'),

    # Invoice PDF
    path('invoices/<int:invoice_id>/upload-pdf/', views.invoice_upload_pdf, name='invoice_upload_pdf'),
    path('invoices/<int:invoice_id>/download-pdf/', views.invoice_download_pdf, name='invoice_download_pdf'),

    # Default routes
    path('', views.dashboard, name='index'),
]
