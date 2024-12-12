from django.core.management.base import BaseCommand
from django.conf import settings
from wagtail_airtable.importer import AirtableModelImporter
from wagtail_airtable.utils import get_validated_models
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import data from an Airtable and overwrite model or page information"

    def add_arguments(self, parser):
        parser.add_argument(
            "model_name",
            help="Model (as app_label.model_name) or app name to populate table entries for, e.g. creditcards.CreditCard",
        )

    def handle(self, *args, **options):
        # Overwrite verbosity if WAGTAIL_AIRTABLE_DEBUG is enabled.
        if settings.DEBUG:
            # AIRTABLE_DEBUG can only be enabled if standard Django DEBUG is enabled.
            # The idea is to protect logs and output in production from the noise of these imports.
            AIRTABLE_DEBUG = getattr(settings, "WAGTAIL_AIRTABLE_DEBUG", False)
            if AIRTABLE_DEBUG:
                options["verbosity"] = 2

        model = get_validated_models([options["model_name"]])[0]
        importer = AirtableModelImporter(model=model, verbosity=options["verbosity"])

        error_results = []
        new_results = []
        updated_results = []

        for result in importer.run():
            if result.errors:
                logger.error("Failed to import %s %s", result.record_id, result.errors)
                error_results.append(result)
            elif result.new:
                new_results.append(result)
            else:
                updated_results.append(result)

        return f"{len(new_results)} objects created. {len(updated_results)} objects updated. {len(error_results)} objects skipped due to errors."
