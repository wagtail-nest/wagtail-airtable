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
    Handles generation of URL depending on the Wagtail version used
    Addresses the changes in route names within the wagtailsnippets namespace in Wagtail v4.
    https://docs.wagtail.org/en/stable/releases/4.0.html#url-route-names-for-image-document-and-snippet-apps-have-changed

    Takes the label and the model as arguments.

    Use:
    {% load wagtail_airtable_tags %}
    {% wagtail_route 'wagtailsnippets:list' model_opts.app_label model_opts.model_name %}

    Returns a URL.
    """
    tokens = name.split(":")
    name = "_".join([tokens[0], label, model]) + f":{tokens[1]}"
    url = reverse(name, args=args)

    return url


@register.simple_tag
def wagtail_major_version() -> int:
    """
    Returns the major version of Wagtail as an integer.
    """
    return WAGTAIL_VERSION[0]
