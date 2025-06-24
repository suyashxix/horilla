"""
horilla_apps

This module is used to register horilla addons
"""


import os
from horilla import settings as custom_settings         # your project's settings (for env)
from django.conf import settings as django_settings     # Django's internal settings

INSTALLED_APPS = django_settings.INSTALLED_APPS




# Conditionally add storages
if custom_settings.env("AWS_ACCESS_KEY_ID", default=None) and "storages" not in INSTALLED_APPS:
    INSTALLED_APPS.append("storages")


AUDITLOG_INCLUDE_ALL_MODELS = True

AUDITLOG_EXCLUDE_TRACKING_MODELS = (
    # "<app_name>",
    # "<app_name>.<model>"
)

setattr(custom_settings, "AUDITLOG_INCLUDE_ALL_MODELS", AUDITLOG_INCLUDE_ALL_MODELS)
setattr(custom_settings, "AUDITLOG_EXCLUDE_TRACKING_MODELS", AUDITLOG_EXCLUDE_TRACKING_MODELS)


SETTINGS_EMAIL_BACKEND = getattr(custom_settings, "EMAIL_BACKEND", False)
setattr(custom_settings, "EMAIL_BACKEND", "base.backends.ConfiguredEmailBackend")
if SETTINGS_EMAIL_BACKEND:
    setattr(custom_settings, "EMAIL_BACKEND", SETTINGS_EMAIL_BACKEND)


SIDEBARS = [
    "recruitment",
    "onboarding",
    "employee",
    "attendance",
    "leave",
    "payroll",
    "pms",
    "offboarding",
    "asset",
    "helpdesk",
    "project",
    "invoicing"
]

WHITE_LABELLING = False
NESTED_SUBORDINATE_VISIBILITY = False
TWO_FACTORS_AUTHENTICATION = False
