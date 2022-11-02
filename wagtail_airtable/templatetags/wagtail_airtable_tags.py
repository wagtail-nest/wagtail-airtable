from django import template
from django.conf import settings
from django.urls import reverse
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
def wagtail_route(name, label, model, *args) -> str:
    """
    Return the wagtail URL using the label and model.

    Use:
    {% load wagtail_airtable_tags %}
    {% can_import_model "yourapp.ModelName" as template_var %}

    Returns a URL.
    """
    if WAGTAIL_VERSION >= (4, 0):
        tokens = name.split(":")
        name = "_".join([tokens[0], label, model]) + f":{tokens[1]}"
        url = reverse(name, args=args)
    else:
        url = reverse(name, args=[label, model, *args])
    return url
