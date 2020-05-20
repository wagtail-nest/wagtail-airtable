"""
Utility functions for wagtail-airtable.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist


def get_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the model class
    """
    app_label, model_name = model_path.lower().split(".")
    return ContentType.objects.get_by_natural_key(
        app_label, model_name
    ).model_class()

def get_all_models() -> set:
    """
    Get's all models from settings.AIRTABLE_IMPORT_SETTINGS.

    Returns a set (unique and unordered list of models)
    """
    airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})
    validated_models = set()
    for label, model_settings in airtable_settings.items():
        if model_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
            label = label.lower()
            if "." in label:
                try:
                    model = get_model_for_path(label)
                    validated_models.add(model)
                except ObjectDoesNotExist:
                    raise CommandError(
                        "%r is not recognised as a model name." % label
                    )

    return validated_models
