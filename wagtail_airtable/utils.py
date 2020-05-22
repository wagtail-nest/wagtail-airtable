"""
Utility functions for wagtail-airtable.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist


def get_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the model class or False
    """
    app_label, model_name = model_path.lower().split(".")
    try:
        return ContentType.objects.get_by_natural_key(
            app_label, model_name
        ).model_class()
    except ObjectDoesNotExist:
        return False


def get_all_models() -> list:
    """
    Gets all models from settings.AIRTABLE_IMPORT_SETTINGS.

    Returns a list of models.
    """
    airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})
    validated_models = []
    for label, model_settings in airtable_settings.items():
        if model_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
            label = label.lower()
            if "." in label:
                try:
                    model = get_model_for_path(label)
                    validated_models.append(model)
                except ObjectDoesNotExist:
                    raise ImproperlyConfigured(
                        "%r is not recognised as a model name." % label
                    )

    return validated_models


def get_validated_models(models=[]) -> list:
    """
    Accept a list of model paths (ie. ['appname.Model1', 'appname.Model2']).

    Looks for models from a string and checks if the mode actually exists.
    Then it'll loop through each model and check if it's allowed to be imported.

    Returns a list of validated models.
    """
    validated_models = []
    for label in models:
        if "." in label:
            # interpret as a model
            model = get_model_for_path(label)
            if not model:
                raise ImproperlyConfigured("%r is not recognised as a model name." % label)

            validated_models.append(model)

    models = validated_models[:]
    for model in validated_models:
        airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(
            model._meta.label, {}
        )
        # Remove this model from the `models` list so it doesn't hit the Airtable API.
        if not airtable_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
            models.remove(model)

    return models
