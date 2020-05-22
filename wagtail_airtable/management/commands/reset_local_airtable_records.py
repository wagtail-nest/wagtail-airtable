from django.conf import settings
from django.core.management.base import BaseCommand

from wagtail_airtable.utils import get_all_models


class Command(BaseCommand):
    help = "Looks through every available model in the AIRTABLE_IMPORT_SETTINGS and unsets the `airtable_record_id`"

    def handle(self, *args, **options):
        """
        Gets all the models set in AIRTABLE_IMPORT_SETTINGS, loops through them, and set `airtable_record_id=''` to every one.
        """
        records_updated = 0
        models = get_all_models()
        for model in models:
            if hasattr(model, "airtable_record_id"):
                total_updated = model.objects.update(airtable_record_id="")
                records_updated = records_updated + total_updated

        if options["verbosity"] >= 1:
            self.stdout.write(f"Set {records_updated} objects to airtable_record_id=''")
