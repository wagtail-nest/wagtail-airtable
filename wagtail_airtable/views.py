from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.core.exceptions import ObjectDoesNotExist
from logging import getLogger

from wagtail_airtable.forms import AirtableImportModelForm
from wagtail_airtable.utils import get_model_for_path

from wagtail_airtable.management.commands.import_airtable import Importer

logger = getLogger(__name__)


class AirtableImportListing(TemplateView):
    """
    Loads options for importing Airtable data
    """

    template_name = "wagtail_airtable/airtable_import_listing.html"
    http_method_names = ["get", "post"]

    def post(self, request, *args, **kwargs):
        form = AirtableImportModelForm(request.POST)
        if form.is_valid():
            model_label = form.cleaned_data["model"]
            importer = Importer(models=[model_label], options={"verbosity": 1})
            importer.run()
            message = f"{importer.created} items created. {importer.updated} items updated. {importer.skipped} items skipped."
            messages.add_message(
                request, messages.SUCCESS, f"Import succeeded with {message}"
            )
        else:
            messages.add_message(request, messages.ERROR, "Could not import")

        return redirect(reverse("airtable_import_listing"))

    def _get_base_model(self, model):
        """
        For the given model, return the highest concrete model in the inheritance tree -
        e.g. for BlogPage, return Page
        """
        if model._meta.parents:
            model = model._meta.get_parent_list()[0]
        return model

    def get_validated_models(self):
        """Get models from AIRTABLE_IMPORT_SETTINGS, validate they exist, and return a list of tuples.

        returns:
            [
                ('Credit Card', 'creditcards.CreditCard', <CreditCard: Cardname.=>),
                ('..', '..'),
            ]
        """
        airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})

        # Loop through all the models in the settings and create a new dict
        # of the unique settings for each model label.
        # If settings were used more than once the second (3rd, 4th, etc) common settings
        # will be bulked into a "grouped_models" list.
        tracked_settings = []
        models = {}
        for label, model_settings in airtable_settings.items():
            if model_settings not in tracked_settings:
                tracked_settings.append(model_settings)
                models[label] = model_settings
                models[label]["grouped_models"] = []
            else:
                for label2, model_settings2 in models.items():
                    if model_settings is model_settings2:
                        models[label2]["grouped_models"].append(label)

        # Validated models are models that actually exist.
        # This way fake models can't be added.
        validated_models = []
        for label, model_settings in models.items():
            # If this model is allowed to be imported. Default is True.
            if model_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
                # A temporary variable for holding grouped model names.
                # This is added to the validated_models item later.
                # This is only used for displaying model names in the import template
                _grouped_models = []
                # Loop through the grouped_models list in each setting, validate each model,
                # then add it to the larger grouped_models
                if model_settings.get("grouped_models"):
                    for grouped_model_label in model_settings.get("grouped_models"):
                        if "." in grouped_model_label:
                            model = get_model_for_path(grouped_model_label)
                            if model:
                                _grouped_models.append(model._meta.verbose_name_plural)

                if "." in label:
                    model = get_model_for_path(label)
                    if model:
                        # Append a triple-tuple to the validated_models with the:
                        # (1. Models verbose name, 2. Model label, 3. is_airtable_enabled from the model, and 4. List of grouped models)
                        airtable_enabled_for_model = getattr(
                            model, "is_airtable_enabled", False
                        )
                        validated_models.append(
                            (
                                model._meta.verbose_name_plural,
                                label,
                                airtable_enabled_for_model,
                                _grouped_models,
                            )
                        )
                    else:
                        raise ImproperlyConfigured(
                            "%r is not recognised as a model name." % label
                        )

        return validated_models

    def get_context_data(self, **kwargs):
        """Add validated models from the AIRTABLE_IMPORT_SETTINGS to the context."""
        return {"models": self.get_validated_models()}
