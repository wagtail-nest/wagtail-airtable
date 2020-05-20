"""
Utility functions for wagtail-airtable.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError


def get_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the model class
    """
    app_label, model_name = model_path.lower().split(".")
    return ContentType.objects.get_by_natural_key(
        app_label, model_name
    ).model_class()

def get_all_models() -> list:
    """
    Get's all models from settings.AIRTABLE_IMPORT_SETTINGS.

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
                    raise CommandError(
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
            try:
                model = get_model_for_path(label)
            except ObjectDoesNotExist:
                raise CommandError("%r is not recognised as a model name." % label)

            validated_models.append(model)

    models = validated_models[:]
    for model in validated_models:
        airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(
            model._meta.label, {}
        )
        # Remove this model the the `models` list so it doesn't hit the Airtable API.
        if not airtable_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
            models.remove(model)

    return models
