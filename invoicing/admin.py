from django.contrib import admin
from .models import Client, Placement, Invoice, InvoiceNotification, InvoiceHistory
# Register your models here.


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'company']
    search_fields = ['name', 'contact_person', 'email']
    list_editable = ['is_active']

@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'client', 'position', 'joining_date', 'notice_period_days', 'placement_fee', 'is_invoice_eligible']
    list_filter = ['joining_date', 'is_active', 'client', 'created_at']
    search_fields = ['candidate__first_name', 'candidate__last_name', 'client__name', 'position']
    date_hierarchy = 'joining_date'
    
    def is_invoice_eligible(self, obj):
        return obj.is_invoice_eligible
    is_invoice_eligible.boolean = True
    is_invoice_eligible.short_description = 'Invoice Eligible'

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'placement', 'amount', 'total_amount', 'status', 'issue_date', 'due_date', 'is_overdue']
    list_filter = ['status', 'issue_date', 'due_date', 'sent_at']
    search_fields = ['invoice_number', 'placement__candidate__first_name', 'placement__client__name']
    readonly_fields = ['invoice_number', 'total_amount', 'created_at', 'updated_at']
    date_hierarchy = 'issue_date'
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'

@admin.register(InvoiceNotification)
class InvoiceNotificationAdmin(admin.ModelAdmin):
    list_display = ['placement', 'notification_type', 'is_read', 'notified_user', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['placement__candidate__first_name', 'placement__client__name']

@admin.register(InvoiceHistory)
class InvoiceHistoryAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['old_status', 'new_status', 'changed_at']
    search_fields = ['invoice__invoice_number']
    readonly_fields = ['changed_at']