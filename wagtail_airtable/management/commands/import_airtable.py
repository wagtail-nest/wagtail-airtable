from importlib import import_module

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

    def _find_parent_model(self, model_label) -> dict:
        """
        Loop through all the AIRTABLE_IMPORT_SETTINGS, and look for EXTRA_SUPPORTED_MODELS.

        If there is an EXTRA_SUPPORTED_MODELS key, check if the current model is in the list of
        models.

        If the `model` is in the list of EXTRA_SUPPORTED_MODELS, return the parent dictionary.
        """
        return_settings = {}
        for model_path, model_settings in settings.AIRTABLE_IMPORT_SETTINGS.items():
            if model_settings.get("EXTRA_SUPPORTED_MODELS"):
                models_lower = [x.lower() for x in model_settings.get("EXTRA_SUPPORTED_MODELS")]
                if model_label.lower() in models_lower:
                    return_settings = settings.AIRTABLE_IMPORT_SETTINGS[model_path]

        return return_settings


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
        # Overwrite verbosity if WAGTAIL_AIRTABLE_DEBUG is enabled.
        if settings.DEBUG:
            # AIRTABLE_DEBUG can only be enabled if standard Django DEBUG is enabled.
            # The idea is to protect logs and output in production from the noise of these imports.
            AIRTABLE_DEBUG = getattr(settings, 'WAGTAIL_AIRTABLE_DEBUG', False)
            if AIRTABLE_DEBUG:
                options['verbosity'] = 2

        def debug_message(message):
            """
            Local function. Print debug messages if `verbosity` is 2 or higher.
            """
            if options['verbosity'] >= 2:
                print(message)

        validated_models = []
        for label in options['labels']:
            label = label.lower()
            if '.' in label:
                # interpret as a model
                try:
                    model = self.get_model_for_path(label)
                except ObjectDoesNotExist:
                    raise CommandError("%r is not recognised as a model name." % label)

                validated_models.append(model)

        # Loop through each of the validated moels, and look for `EXTRA_SUPPORTED_MODELS`
        models = validated_models[:]
        for model in validated_models:
            airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(model._meta.label, {})
            # If not allowed to import this model, don't allow EXTRA_SUPPORTED_MODELS either.
            # Remove this model the the `models` list so it doesn't hit the Airtable API.
            if not airtable_settings.get("AIRTABLE_IMPORT_ALLOWED", True):
                models.remove(model)
                continue

            if airtable_settings.get("EXTRA_SUPPORTED_MODELS"):
                for label in airtable_settings.get("EXTRA_SUPPORTED_MODELS"):
                    label = label.lower()
                    if '.' in label:
                        # interpret as a model
                        try:
                            model = self.get_model_for_path(label)
                        except ObjectDoesNotExist:
                            raise CommandError("%r is not recognised as a model name." % label)

                        models.append(model)

        debug_message(f"Validated models: {models}")

        # Used for re-using API data instead of making several of API request and waiting/spamming the Airtable API
        cached_records = {}
        # Maintain a list of record Ids that were used already. Every record is a unique ID so processing the
        # Same record more than once will just be hitting the DB over and over and over again. No bueno.
        records_used = []
        created = 0
        updated = 0
        skipped = 0
        for model in models:
            debug_message(f"IMPORTING MODEL: {model}")
            # Wagtail models require a .save_revision() call when being saved.
            is_wagtail_model = hasattr(model, 'depth')
            # Airtable global settings.
            airtable_settings = settings.AIRTABLE_IMPORT_SETTINGS.get(model._meta.label, {})
            if not airtable_settings:
                # This could be an EXTRA_SUPPORTED_MODEL in which case we need to use it's parent settings.
                airtable_settings = self._find_parent_model(model._meta.label_lower)
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

            # Set the Airtable API client on a per-model basis
            airtable = Airtable(
                airtable_settings.get('AIRTABLE_BASE_KEY'),
                airtable_settings.get('AIRTABLE_TABLE_NAME'),
                api_key=settings.AIRTABLE_API_KEY,
            )

            # Memoize results from Airtable so we don't hit the same API multiple times
            # This is largely used to support EXTRA_SUPPORTED_MODELS as they would use the
            # same Airtable based as the key in the dictionary.
            #   ie.
            #   'yourapp.YourPage': {
            #       ...
            #       'AIRTABLE_TABLE_NAME': 'Your Table',
            #       'EXTRA_SUPPORTED_MODELS': ['yourapp.Page2', 'yourapp.Page3']
            #   }
            #   All of the above EXTRA_SUPPORTED_MODELS will use the 'Your Table' results
            #   instead of hitting the Airtable API for each model and getting the same
            #   results every time
            if cached_records.get(airtable.table_name):
                all_records = cached_records.get(airtable.table_name)
            else:
                # Get all the airtable records for the specified table.
                # TODO try/catch this in case of misconfiguration.
                all_records = airtable.get_all()
                cached_records[airtable.table_name] = all_records

            debug_message(f"\t Airtable base key: {airtable_settings.get('AIRTABLE_BASE_KEY')}")
            debug_message(f"\t Airtable table name: {airtable_settings.get('AIRTABLE_TABLE_NAME')}")
            debug_message(f"\t Airtable unique identifier settings:")
            debug_message(f"\t Airtable records: {len(all_records)}")
            debug_message(f"\t\t Airtable column: {airtable_unique_identifier_column_name}")
            debug_message(f"\t\t Django field name: {airtable_unique_identifier_field_name}")

            # Loop through every record in the Airtable.
            for record in all_records:
                # If a record was used already, skip this iteration.
                if record['id'] in records_used:
                    continue

                debug_message("")  # Empty space for nicer debug statement separation
                record_id = record['id']
                record_fields = record['fields']
                mapped_import_fields = model.map_import_fields(incoming_dict_fields=record_fields)
                # Create a dictionary of newly mapped key:value pairs based on the `mappings` dict above.
                # This wil convert "airtable column name" to "django_field_name"
                mapped_import_fields = {
                    mapped_import_fields[key]: value for (key, value) in record_fields.items() if key in mapped_import_fields
                }
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
                        # This could theoretically cause a loop. By default this setting is False. But the
                        # below line confirms it's false, just to be safe.
                        obj.airtable_record_id = record_id
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
                            # New record being processed. Save it to the list of records.
                            records_used.append(record['id'])
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
                    debug_message(f"\t\t An Airtable record based on the unique identifier was found: {airtable_unique_identifier_column_name}")

                    try:
                        obj = model.objects.get(**{airtable_unique_identifier_field_name: unique_identifier})
                        debug_message(f"\t\t Local object found by Airtable unique column name: {airtable_unique_identifier_column_name}")
                    except model.DoesNotExist:
                        obj = None
                        debug_message("\t\t No object was found based on the Airtable column name")

                    if obj:
                        # A local model object was found by a unique identifier.
                        if serialized_data.is_valid():
                            for field_name, value in serialized_data.validated_data.items():
                                if field_name == "tags":
                                    for tag in value:
                                        obj.tags.add(tag)
                                else:
                                    setattr(obj, field_name, value)
                            # When an object is saved it should NOT push its newly saved data back to Airtable.
                            # This could theoretically cause a loop. By default this setting is False. But the
                            # below line confirms it's false, just to be safe.
                            obj.airtable_record_id = record_id
                            obj.push_to_airtable = False
                            try:
                                if is_wagtail_model:
                                    # Wagtail page. Requires a .save_revision()
                                    if not obj.locked:
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
                                    obj.save()
                                    debug_message("\t\t\t Saved!")
                                    updated = updated + 1

                                # Record this record as "used"
                                records_used.append(record['id'])
                                # New record being processed. Save it to the list of records.
                                continue
                            except ValidationError as error:
                                error_message = '; '.join(error.messages)
                                logger.error(f"Unable to save {obj}. Error(s): {error_message}")
                                debug_message(f"\t\t Unable to save {obj} (ID: {obj.pk}; Airtable Record ID: {record_id}). Reason: {error_message}")
                                skipped = skipped + 1
                        else:
                            logger.info(f"Invalid data for record {record_id}")
                            debug_message(f"\t\t Serializer data was invalid.")
                            skipped = skipped + 1
                    else:
                        # No object was found by this unique ID.
                        # Do nothing. The next step will be to create this object in Django
                        logger.info(f"{model._meta.verbose_name} with field {airtable_unique_identifier_field_name}={unique_identifier} was not found")
                        debug_message(f"\t\t {model._meta.verbose_name} with field {airtable_unique_identifier_field_name}={unique_identifier} was not found")
                        skipped = skipped + 1
                else:
                    # There was no unique identifier set for this model.
                    # Nothing can be done about that right now.
                    logger.info(f"{model._meta.verbose_name} does not have a unique identifier")
                    debug_message(f"\t\t {model._meta.verbose_name} does not have a unique identifier")
                    skipped = skipped + 1

                # Cannot bulk-create Wagtail pages from Airtable because we don't know where the pages
                # Are supposed to live, what their tree depth should be, and a few other factors.
                # For this scenario, log information and skip the loop iteration.
                if hasattr(model, 'depth'):
                    logger.info(f"{model._meta.verbose_name} cannot be created from an import.")
                    debug_message(f"\t\t {model._meta.verbose_name} is a Wagtail Page and cannot be created from an import.")
                    # New record being processed. Save it to the list of records.
                    records_used.append(record['id'])
                    continue


                # First things first, remove any "pk" or "id" items form the mapped_import_fields
                # This will let Django and Wagtail handle the PK on its own, as it should.
                # When the model is saved it'll trigger a push to Airtable and automatically update
                # the necessary column with the new PK so it's always accurate.
                try:
                    del mapped_import_fields['pk']
                except KeyError:
                    pass
                try:
                    del mapped_import_fields['id']
                except KeyError:
                    pass

                # If there is no match whatsoever, try to create a new `model` instance.
                # Note: this may fail if there isn't enough data in the Airtable record.
                try:
                    debug_message(f"\t\t Attempting to create a new object...")
                    mapped_import_fields['airtable_record_id'] = record_id
                    model.objects.create(**mapped_import_fields)
                    debug_message(f"\t\t Object created")
                    created = created + 1
                except ValueError as value_error:
                    logger.info(f"Could not create new model. Error: {value_error}")
                    debug_message(f"\t\t Could not create new model. Error: {value_error}")
                except IntegrityError as e:
                    logger.info(f"Could not create new model. Error: {e}")
                    debug_message(f"\t\t Could not create new model. Error: {e}")
                except AttributeError as e:
                    logger.info(f"Could not create new model. AttributeError. Error: {e}")
                    debug_message(f"\t\t Could not create new model. AttributeError. Error: {e}")
                except Exception as e:
                    logger.error(f"Unhandled error. Could not create a new object for {model._meta.verbose_name}. Error: {e}")
                    debug_message(f"\t\t Unhandled error. Could not create a new object for {model._meta.verbose_name}. Error: {e}")


        if options['verbosity'] >= 1:
            self.stdout.write(f"{created} objects created. {updated} objects updated. {skipped} objects skipped. {len(records_used)} total records used.")

        return f"{created} objects created. {updated} objects updated. {skipped} objects skipped. {len(records_used)} total records used."


