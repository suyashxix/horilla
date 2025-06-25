from django import template

register = template.Library()

@register.filter
def split(value, key):
    """
    Split a string by the given key
    Usage: {{ "apple,banana,orange"|split:"," }}
    """
    if not value:
        return []
    return value.split(key)

@register.filter
def trim(value):
    """
    Trim whitespace from string
    Usage: {{ " hello world "|trim }}
    """
    if not value:
        return ""
    return value.strip()
