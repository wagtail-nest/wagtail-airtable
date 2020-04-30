from importlib import import_module
from requests import HTTPError

from airtable import Airtable
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.core.management.base import BaseCommand, CommandError
from logging import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Import data from an Airtable and overwrite model or page information"

    def add_arguments(self, parser):
        parser.add_argument('labels', metavar='model_name', nargs='+', help="Model (as app_label.model_name) or app name to populate table entries for, e.g. creditcards.CreditCard")

    def get_model_for_path(self, model_path):
        """
        Given an 'app_name.model_name' string, return the model class
        """
        app_label, model_name = model_path.split('.')
        return ContentType.objects.get_by_natural_key(app_label, model_name).model_class()

    def get_model_serializer(self, serializer_string):
        location, serializer_name = serializer_string.rsplit(".", 1)
        module = import_module(location)
        serializer_class = getattr(module, serializer_name)
        return serializer_class

    def handle(self, *args, **options):
        """
        Runs the management command with the app_name.ModelName as parameters.
        ie. python manage.py import_airtable pages.HomePage creditcards.CreditCard

        This will handle Wagtail Pages (with page revisions) along with standard
        Django models.

        Models passed in to the command go through a quick validation to ensure they
        exist.

        Every model is then looped through, and a `settings.AIRTABLE_IMPORT_SETTINGS`
        is searched for based on the models label (ie. pages.HomePage). These
        settings are used to connect to a certain Airtable Base (a set of spreadsheets),
        the name of the table to use, a unique identifier (used for connecting previously
        unrelated Airtable records to Django objects), and a serializer for validating
        incoming data from Airtable to make it work with the Django field types.

        Within each model loop also contains an `airtable.get_all()` command which
        will get all the data from the Airtable spreadsheet and load it into a
        list of dictionaries.

        Then every record is iterated over and 3 actions are taken:
            1. Look for an existing model object by its airtable_record_id.
               Update if found. Skip to step 2 if not found.
            2. Search for a model object by its unique identifier.
               If found, update the object. Skip to step 3 if not found.
            3. Create a new object. This step is very susceptible to fail based on the
               model type and fields in the serializer. Wagtail pages cannot be created
               from Airtable records as there's missing data such as depth and parent
               pages. And so Wagtail pages are skipped entirely in step 3.
        """
        # TODO Move the AIRTABLE_DEBUG logic to a diff file.
        # If Airtable debug is enabled and this function is called print() statements will appear in your terminal.
        # CAUTION: Do NOT run this in production
        AIRTABLE_DEBUG = False
        if settings.DEBUG:
            # AIRTABLE_DEBUG can only be enabled if standard Django DEBUG is enabled.
            # The idea is to protect logs and output in production from the noise of these imports.
            AIRTABLE_DEBUG = getattr(settings, 'WAGTAIL_AIRTABLE_DEBUG', False)

        def debug_message(message):
            if AIRTABLE_DEBUG:
                print(message)

        models = []
        for label in options['labels']:
            label = label.lower()
            if '.' in label:
                # interpret as a model
                try:
                    model = self.get_model_for_path(label)
                except ObjectDoesNotExist:
                    raise CommandError("%r is not recognised as a model name." % label)

                models.append(model)

        debug_message(f"Validated models: {models}")
        created = 0
        updated = 0
        skipped = 0
        for model in models:
            debug_message(f"IMPORTING MODEL: {model}")
            # Wagtail models require a .save_revision() call when being saved.
            is_wagtail_model = hasattr(model, 'depth')
            # Airtable global settings.
            airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(model._meta.label, {})
            # Set the unique identifier and serializer.
            airtable_unique_identifier = airtable_settings.get('AIRTABLE_UNIQUE_IDENTIFIER')
            model_serializer = self.get_model_serializer(airtable_settings.get('AIRTABLE_SERIALIZER'))

            if type(airtable_unique_identifier) == str:
                # The unique identifier is a string.
                # Use it as the Airtable Column name and the Django field name
                airtable_unique_identifier_column_name = airtable_unique_identifier
                airtable_unique_identifier_field_name = airtable_unique_identifier
            elif type(airtable_unique_identifier) == dict:
                # Unique identifier is a dictionary.
                # Use the key as the Airtable Column name and the value as the Django Field name.
                airtable_unique_identifier_column_name, airtable_unique_identifier_field_name = (
                    list(airtable_unique_identifier.items())[0]
                )

            # Set the Airtable API client.
            airtable = Airtable(
                airtable_settings.get('AIRTABLE_BASE_KEY'),
                airtable_settings.get('AIRTABLE_TABLE_NAME'),
                api_key=settings.AIRTABLE_API_KEY,
            )

            # Get all the airtable records for the specified table.
            # TODO try/catch this in case of misconfiguration.
            all_records = airtable.get_all()
            debug_message(f"\t Airtable base key: {airtable_settings.get('AIRTABLE_BASE_KEY')}")
            debug_message(f"\t Airtable table name: {airtable_settings.get('AIRTABLE_TABLE_NAME')}")
            debug_message(f"\t Airtable unique identifier settings:")
            debug_message(f"\t\t Airtable column: {airtable_unique_identifier_column_name}")
            debug_message(f"\t\t Django field name: {airtable_unique_identifier_field_name}")
            debug_message(f"\t Airtable records: {len(all_records)}")

            # Loop through every record in the Airtable.
            for record in all_records:
                debug_message("") # Empty space for nicer debug statement separation
                record_id = record['id']
                record_fields = record['fields']
                mapped_import_fields = model.map_import_fields(incoming_dict_fields=record_fields)
                serialized_data = model_serializer(data=mapped_import_fields)
                serialized_data.is_valid()

                # Look for a record by it's airtable_record_id.
                # If it exists, update the data.
                debug_message(f"\t Looking for existing object with record: {record_id}")
                try:
                    obj = model.objects.get(airtable_record_id=record_id)
                    debug_message(f"\t\t Local object found {obj}")
                except model.DoesNotExist:
                    obj = None
                    debug_message("\t\t Local object was NOT found")

                if obj:
                    # Model object was found by it's airtable_record_id
                    if serialized_data.is_valid():
                        debug_message("\t\t Serializer data was valid. Setting attrs on model...")
                        for field_name, value in serialized_data.validated_data.items():
                            if field_name == "tags":
                                for tag in value:
                                    obj.tags.add(tag)
                            else:
                                setattr(obj, field_name, value)
                        # When an object is saved it should NOT push its newly saved data back to Airtable.
                        # This could theoretically cause a loop
                        obj.push_to_airtable = False
                        try:
                            if is_wagtail_model:
                                debug_message("\t\t This is a Wagtail Page model")
                                # Wagtail page. Requires a .save_revision()
                                if not obj.locked:
                                    debug_message("\t\t\t Page is not locked. Saving page and creating a new revision.")
                                    # Only save the page if the page is not locked
                                    obj.save()
                                    obj.save_revision()
                                    updated = updated + 1
                                else:
                                    # TODO Add a handler to manage locked pages.
                                    debug_message("\t\t\t Page IS locked. Skipping Page save.")
                                    skipped = skipped + 1
                            else:
                                # Django model. Save normally.
                                debug_message("\t\t Saving Django model")
                                obj.save()
                                updated = updated + 1
                        except ValidationError as error:
                            skipped = skipped + 1
                            error_message = '; '.join(error.messages)
                            logger.error(f"Unable to save {obj._meta.label} -> '{obj}'. Error(s): {error_message}")
                            debug_message(f"\t\t Could not save Wagtail/Django model. Error: {error_message}")
                        continue
                    else:
                        logger.info(f"Invalid data for record {record_id}")
                        debug_message(f"\t\t Serializer was invalid for record: {record_id}, model id: {obj.pk}")
                        debug_message(f"\t\t Continuing to look for object by its unique identifier: {airtable_unique_identifier_column_name}...")

                # This `unique_identifier` is the value of an Airtable record.
                # ie.
                #   fields = {
                #         'Slug': 'your-model'
                #   }
                # This will return 'your-model' and can now be searched for as model.objects.get(slug='your-model')
                unique_identifier = record_fields.get(airtable_unique_identifier_column_name, None)
                if unique_identifier:
                    debug_message(f"\t\t A record based on the unique identifier was found: {unique_identifier}")

                    try:
                        obj = model.objects.get(**{airtable_unique_identifier_field_name: unique_identifier})
                        debug_message(f"\t\t Unique identifier exists as Airtable Column Name: {airtable_unique_identifier_column_name}")
                    except model.DoesNotExist:
                        obj = None
                    if obj:
                        # A local model object was found by a unique identifier.

                        if serialized_data.is_valid():
                            for field_name, value in serialized_data.validated_data.items():
                                if field_name == "tags":
                                    for tag in value:
                                        obj.tags.add(tag)
                                else:
                                    setattr(obj, field_name, value)
                            obj.airtable_record_id = record_id
                            obj.push_to_airtable = False
                            try:
                                if is_wagtail_model:
                                    # Wagtail page. Requires a .save_revision()
                                    if not obj.locked:
                                        # Only save the page if the page is not locked
                                        obj.save()
                                        obj.save_revision()
                                    else:
                                        # TODO Add a handler to manage locked pages.
                                        pass
                                else:
                                    # Django model. Save normally.
                                    obj.save()
                                updated = updated + 1
                            except ValidationError as error:
                                error_message = '; '.join(error.messages)
                                logger.error(f"Unable to save {obj}. Error(s): {error_message}")
                        else:
                            logger.info(f"Invalid data for record {record_id}")
                            skipped = skipped + 1
                        continue
                    else:
                        # No object was found by this unique ID.
                        # Do nothing. The next step will be to create this object in Django
                        logger.info(f"{model._meta.verbose_name} with field {airtable_unique_identifier_field_name}={unique_identifier} was not found")
                else:
                    # There was no unique identifier set for this model.
                    # Nothing can be done about that right now.
                    logger.info(f"{model._meta.verbose_name} does not have a unique identifier")

                # Cannot bulk-create Wagtail pages from Airtable because we don't know where the pages
                # Are supposed to live, what their tree depth should be, and a few other factors.
                # For this scenario, log information and skip the loop iteration.
                if hasattr(model, 'depth'):
                    logger.info(f"{model._meta.verbose_name} cannot be created from an import.")
                    skipped = skipped + 1
                    continue

                # If there is no match whatsoever, try to create a new `model` instance.
                # Note: this may fail if there isn't enough data in the Airtable record.
                try:
                    model.objects.create(**mapped_import_fields)
                    created = created + 1
                except ValueError as value_error:
                    logger.info(f"Could not create new model. Error: {value_error}")
                except IntegrityError as e:
                    logger.info(f"Could not create new model. Error: {e}")
                except AttributeError as e:
                    logger.info(f"Could not create new model. AttributeError. Error: {e}")
                except Exception as e:
                    logger.error(f"Unhandled error. Could not create a new object for {model._meta.verbose_name}. Error: {e}")

        if options['verbosity'] >= 1:
            self.stdout.write(f"{created} objects created. {updated} objects updated. {skipped} objects skipped.")
            return f"{created} objects created. {updated} objects updated. {skipped} objects skipped."


