import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, RedirectView
from rest_framework import fields
from wagtail.core.rich_text import expand_db_html
from django.core.exceptions import ObjectDoesNotExist
from logging import getLogger

from project.fastly_cache_backend import purge_key_from_fastly_cache

logger = getLogger(__name__)


class AirtableImportListing(TemplateView):
    """
    Loads options for importing Airtable data
    """

    template_name = "wagtail_airtable/airtable_import_listing.html"

    def dispatch(self, request, *args, **kwargs):
        if 'import' in request.GET:
            model_label = request.GET.get("import")
            message = call_command("import_airtable", model_label, verbosity=1)
            messages.add_message(request, messages.SUCCESS, f'Import succeeded with {message}')
            return redirect(reverse('airtable_import_listing'))
        return super().dispatch(request, *args, **kwargs)

    def _get_model_for_path(self, model_path):
        """
        Given an 'app_name.model_name' string, return the model class
        """
        app_label, model_name = model_path.split('.')
        return ContentType.objects.get_by_natural_key(app_label, model_name).model_class()

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
        airtable_settings = getattr(settings, 'AIRTABLE_IMPORT_SETTINGS', {})
        validated_models = []

        for label, model_settings in airtable_settings.items():
            label = label.lower()
            if '.' in label:
                try:
                    model = self._get_model_for_path(label)
                    validated_models.append((model._meta.verbose_name.title(), label, model))
                except ObjectDoesNotExist:
                    raise CommandError("%r is not recognised as a model name." % label)

        return validated_models

    def get_context_data(self, **kwargs):
        """Add validated models from the AIRTABLE_IMPORT_SETTINGS to the context."""
        return {
            'models': self.get_validated_models(),
        }
