from django import template
from django.conf import settings

from wagtail import VERSION as WAGTAIL_VERSION


register = template.Library()


@register.simple_tag
def can_import_model(model_label) -> bool:
    """
    Check if a model can be imported based on its model label.

    Use:
    {% load wagtail_airtable_tags %}
    {% can_import_model "yourapp.ModelName" as template_var %}

    Returns True or False.
    """
    airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})
    has_settings = airtable_settings.get(model_label, False)
    return bool(has_settings)


@register.simple_tag
def wagtail_major_version() -> int:
    """
    Returns the major version of Wagtail as an integer.
    """
    return WAGTAIL_VERSION[0]
