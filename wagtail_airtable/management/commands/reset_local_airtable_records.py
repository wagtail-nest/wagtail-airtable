from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Looks through every available model in the AIRTABLE_IMPORT_SETTINGS and unsets the `airtable_record_id`"

    def _get_model_for_path(self, model_path):
        """
        Given an 'app_name.model_name' string, return the model class
        """
        app_label, model_name = model_path.split(".")
        return ContentType.objects.get_by_natural_key(
            app_label, model_name
        ).model_class()

    def get_all_models(self) -> set:
        airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})
        validated_models = set()
        for label, model_settings in airtable_settings.items():
            if model_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
                label = label.lower()
                if "." in label:
                    try:
                        model = self._get_model_for_path(label)
                        validated_models.add(model)
                    except ObjectDoesNotExist:
                        raise CommandError(
                            "%r is not recognised as a model name." % label
                        )

                    # If there are extra supported models, verify each model is properly loaded
                    # in the settings. But do not add these to the `validated_models` list
                    if model_settings.get("EXTRA_SUPPORTED_MODELS"):
                        for model_path in model_settings.get("EXTRA_SUPPORTED_MODELS"):
                            model_path = model_path.lower()
                            if "." in model_path:
                                try:
                                    model = self._get_model_for_path(model_path)
                                    validated_models.add(model)
                                except ObjectDoesNotExist:
                                    raise CommandError(
                                        "%r is not recognised as a model name."
                                        % model_path
                                    )
        return validated_models

    def handle(self, *args, **options):
        """
        Gets all the models set in AIRTABLE_IMPORT_SETTINGS, loops through them, and set `airtable_record_id=''` to every one.
        """
        records_updated = 0
        models = self.get_all_models()
        for model in models:
            if hasattr(model, "airtable_record_id"):
                total_updated = model.objects.update(airtable_record_id="")
                records_updated = records_updated + total_updated

        if options["verbosity"] >= 1:
            self.stdout.write(f"Set {records_updated} objects to airtable_record_id=''")
