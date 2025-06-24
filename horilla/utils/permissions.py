# horilla/utils/permissions.py

from django.http import HttpResponseForbidden
from functools import wraps
from rest_framework.permissions import BasePermission

# ---- For Django Views ----
def role_required(*allowed_roles):
    """
    Decorator to restrict view access based on user.role
    Usage: @role_required("Admin", "HR")
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required.")

            role = getattr(request.user, "role", None)
            if role not in allowed_roles:
                return HttpResponseForbidden("Permission denied.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# ---- For DRF APIs ----
class RolePermission(BasePermission):
    """
    Permission class for DRF views.
    Usage:
        permission_classes = [RolePermission(["Admin", "Manager"])]
    """
    def __init__(self, roles):
        self.roles = roles

    def has_permission(self, request, view):
        role = getattr(request.user, "role", None)
        return request.user.is_authenticated and role in self.roles
