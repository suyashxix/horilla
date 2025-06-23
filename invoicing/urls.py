from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/create/', views.client_create, name='client_create'),
    
    # Placements
    path('placements/', views.placement_list, name='placement_list'),
    path('placements/create/', views.placement_create, name='placement_create'),
    
    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/<int:placement_id>/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/send/', views.send_invoice_email, name='send_invoice'),
    path('invoices/<int:invoice_id>/pdf/', views.download_invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:invoice_id>/mark-paid/', views.mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/<int:invoice_id>/send-email/', views.send_invoice_email, name='send_invoice_email'),

    path('general-invoices/create/', views.general_invoice_create, name='general_invoice_create'),
    path('general-invoices/<int:invoice_id>/', views.general_invoice_detail, name='general_invoice_detail'),
    path('general-invoices/<int:invoice_id>/pdf/', views.general_invoice_pdf, name='general_invoice_pdf'),
    path('general-invoices/<int:invoice_id>/mark-paid/', views.general_invoice_mark_paid, name='general_invoice_mark_paid'),


    path('', views.dashboard, name='index'),

]
