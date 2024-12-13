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
            "model_names",
            metavar="model_name",
            nargs="+",
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

        error_results = 0
        new_results = 0
        updated_results = 0

        for model in get_validated_models(options["model_names"]):
            importer = AirtableModelImporter(model=model, verbosity=options["verbosity"])

            for result in importer.run():
                if result.errors:
                    logger.error("Failed to import %s %s", result.record_id, result.errors)
                    error_results += 1
                elif result.new:
                    new_results += 1
                else:
                    updated_results += 1

        return f"{new_results} objects created. {updated_results} objects updated. {error_results} objects skipped due to errors."
