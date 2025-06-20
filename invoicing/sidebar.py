# invoicing/sidebar.py

from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse

MENU = "Invoicing"
ACCESSIBILITY = "invoicing.sidebar.menu_accessibility"
IMG_SRC = "images/ui/invoice.svg"  # You'll need to add this icon

SUBMENUS = [
    {
        "menu": "Dashboard",
        "redirect": reverse("invoicing:dashboard"),
        "accessibility": "invoicing.sidebar.dashboard_accessibility",
    },
    {
        "menu": "Clients",
        "redirect": reverse("invoicing:client_list"),
        "accessibility": "invoicing.sidebar.clients_accessibility",
    },
    {
        "menu": "Placements",
        "redirect": reverse("invoicing:placement_list"),
        "accessibility": "invoicing.sidebar.placements_accessibility",
    },
    {
        "menu": "Invoices",
        "redirect": reverse("invoicing:invoice_list"),
        "accessibility": "invoicing.sidebar.invoices_accessibility",
    },
]


def menu_accessibility(
    request, _menu: str = "", user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.is_superuser
        or "invoicing" in user_perms
        or request.user.has_perm("invoicing.view_invoice")
    )


def dashboard_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.is_superuser
        or request.user.has_perm("invoicing.view_invoice")
    )


def clients_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.is_superuser
        or request.user.has_perm("invoicing.view_client")
    )


def placements_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.is_superuser
        or request.user.has_perm("invoicing.view_placement")
    )


def invoices_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.is_superuser
        or request.user.has_perm("invoicing.view_invoice")
    )
