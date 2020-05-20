from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError
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
            importer = Importer(models=[model_label], options={'verbosity': 1})
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
        validated_models = []

        for label, model_settings in airtable_settings.items():
            if model_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
                if "." in label:
                    try:
                        model = get_model_for_path(label)
                        validated_models.append(
                            (model._meta.verbose_name.title(), label, model)
                        )
                    except ObjectDoesNotExist:
                        raise CommandError(
                            "%r is not recognised as a model name." % label
                        )
        models = validated_models[:]
        for title, label, model in validated_models:
            airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(
                model._meta.label, {}
            )
            # Remove this model the the `models` list so it doesn't hit the Airtable API.
            if not airtable_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
                models.remove(model)

        return models

    def get_context_data(self, **kwargs):
        """Add validated models from the AIRTABLE_IMPORT_SETTINGS to the context."""
        return {
            "models": self.get_validated_models(),
        }
