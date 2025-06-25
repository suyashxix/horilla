"""
invoicing/sidebar.py

To set Horilla sidebar for invoicing
"""

from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

MENU = _("Invoicing")
ACCESSIBILITY = "invoicing.sidebar.menu_accessibility"
IMG_SRC = "images/ui/invoice.svg"  

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse("invoicing:dashboard"),
        "accessibility": "invoicing.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("Invoices"),
        "redirect": reverse("invoicing:invoice_list"),
        "accessibility": "invoicing.sidebar.invoices_accessibility",
    },
    {
        "menu": _("Placements"),
        "redirect": reverse("invoicing:placement_list"),
        "accessibility": "invoicing.sidebar.placements_accessibility",
    },
    {
        "menu": _("Clients"),
        "redirect": reverse("invoicing:client_list"),
        "accessibility": "invoicing.sidebar.clients_accessibility",
    },
]


def menu_accessibility(
    request, _menu: str = "", user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can access invoicing module"""
    return (
        request.user.has_perm("invoicing.view_invoice") or
        request.user.has_perm("invoicing.view_generalinvoice") or
        request.user.has_perm("invoicing.view_placement") or
        request.user.has_perm("invoicing.view_client") or
        request.user.is_superuser
    )


def dashboard_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can access invoicing dashboard"""
    return (
        request.user.has_perm("invoicing.view_invoice") or
        request.user.has_perm("invoicing.view_generalinvoice") or
        request.user.is_superuser
    )


def invoices_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can view invoices"""
    return (
        request.user.has_perm("invoicing.view_invoice") or
        request.user.has_perm("invoicing.view_generalinvoice") or
        request.user.is_superuser
    )


def react_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can access React invoicing interface"""
    return (
        request.user.has_perm("invoicing.view_invoice") or
        request.user.has_perm("invoicing.view_generalinvoice") or
        request.user.is_superuser
    )


def placements_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can view placements"""
    return (
        request.user.has_perm("invoicing.view_placement") or
        request.user.has_perm("invoicing.add_invoice") or
        request.user.is_superuser
    )


def clients_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """Check if user can view clients"""
    return (
        request.user.has_perm("invoicing.view_client") or
        request.user.has_perm("invoicing.add_client") or
        request.user.is_superuser
    )



