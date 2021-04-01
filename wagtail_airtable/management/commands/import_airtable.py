import sys
from importlib import import_module

from airtable import Airtable
from django.db import models, IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from logging import getLogger
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.managers import TaggableManager
from wagtail.core.models import Page

from wagtail_airtable.tests import MockAirtable
from wagtail_airtable.utils import get_validated_models

logger = getLogger(__name__)


DEFAULT_OPTIONS = {
    "verbosity": 1,
}

TESTING = any(x in ["test", "runtests.py"] for x in sys.argv)


class Importer:
    def __init__(self, models=[], options=DEFAULT_OPTIONS):
        self.models = models
        self.options = options
        self.records_used = []
        self.cached_records = {}
        self.created = 0
        self.updated = 0
        self.skipped = 0

    def debug_message(self, message):
        """
        Local function. Print debug messages if `verbosity` is 2 or higher.
        """
        if self.options["verbosity"] >= 2:
            if not TESTING:
                print(message)
            return message

    def get_model_serializer(self, serializer_string):
        location, serializer_name = serializer_string.rsplit(".", 1)
        module = import_module(location)
        serializer_class = getattr(module, serializer_name)
        return serializer_class

    def get_model_settings(self, model) -> dict:
        return settings.AIRTABLE_IMPORT_SETTINGS.get(model._meta.label, {})

    def get_column_to_field_names(self, airtable_unique_identifier) -> tuple:
        uniq_id_type = type(airtable_unique_identifier)
        airtable_unique_identifier_column_name = None
        airtable_unique_identifier_field_name = None
        if uniq_id_type == str:
            # The unique identifier is a string.
            # Use it as the Airtable Column name and the Django field name
            airtable_unique_identifier_column_name = airtable_unique_identifier
            airtable_unique_identifier_field_name = airtable_unique_identifier
        elif uniq_id_type == dict:
            # Unique identifier is a dictionary.
            # Use the key as the Airtable Column name and the value as the Django Field name.
            (
                airtable_unique_identifier_column_name,
                airtable_unique_identifier_field_name,
            ) = list(airtable_unique_identifier.items())[0]

        return (
            airtable_unique_identifier_column_name,
            airtable_unique_identifier_field_name,
        )

    def get_or_set_cached_records(self, airtable_client):
        # Memoize results from Airtable so we don't hit the same API multiple times
        # This is largely used to support additional Wagtail/Airatble settings
        # that are identical to each other, as in they would use the
        # same Airtable Base as the key in the dictionary.
        #   ie.
        #   'yourapp.YourPage': {
        #       ...
        #       'AIRTABLE_TABLE_NAME': 'Your Table',
        #   },
        #   'different_app.DifferentPage': {
        #       ...
        #       'AIRTABLE_TABLE_NAME': 'Your Table',  # Same Airtable Table name
        #   }
        #   All of the above settings will use the 'Your Table' results
        #   instead of hitting the Airtable API for each model and getting the same
        #   results every time. This is designed to help with API efficiency, reduce
        #   load/import times, and to reduce how much memory is required to save all
        #   the records from Airtable.
        if self.cached_records.get(airtable_client.table_name):
            all_records = self.cached_records.get(airtable_client.table_name)
        else:
            # Get all the airtable records for the specified table.
            all_records = airtable_client.get_all()
            self.cached_records[airtable_client.table_name] = all_records
        return all_records

    def convert_mapped_fields(self, record_fields_dict, mapped_fields_dict) -> dict:
        # Create a dictionary of newly mapped key:value pairs based on the `mappings` dict above.
        # This wil convert "airtable column name" to "django_field_name"
        mapped_fields_dict = {
            mapped_fields_dict[key]: value
            for (key, value) in record_fields_dict.items()
            if key in mapped_fields_dict
        }
        return mapped_fields_dict

    def update_object(
        self, instance, record_id, serialized_data, is_wagtail_model=False
    ) -> bool:
        """
        Attempts to update an object.

        Returns a bool that determines if the object was updated or not.
        """

        if serialized_data.is_valid():
            self.debug_message(
                "\t\t Serializer data was valid. Setting attrs on model..."
            )
            model = type(instance)
            for field_name, value in serialized_data.validated_data.items():
                field_type = type(
                    model._meta.get_field(field_name)
                )  # ie. django.db.models.fields.CharField
                # If this field type is a subclass of a known Wagtail Tag, or a Django m2m field
                # We need to loop through all the values and add them to the m2m-style field.
                if issubclass(
                    field_type,
                    (TaggableManager, ClusterTaggableManager, models.ManyToManyField,),
                ):
                    m2m_field = getattr(instance, field_name)
                    for m2m_value in value:
                        m2m_field.add(m2m_value)
                else:
                    setattr(instance, field_name, value)
            # When an object is saved it should NOT push its newly saved data back to Airtable.
            # This could theoretically cause a loop. By default this setting is True. But the
            # below line confirms it's false, just to be safe.
            instance.airtable_record_id = record_id
            instance.push_to_airtable = False
            try:
                if is_wagtail_model:
                    self.debug_message("\t\t This is a Wagtail Page model")
                    # Wagtail page. Requires a .save_revision()
                    if not instance.locked:
                        self.debug_message(
                            "\t\t\t Page is not locked. Saving page and creating a new revision."
                        )
                        # Only save the page if the page is not locked
                        instance._skip_signals=True
                        instance.save()
                        instance.save_revision()
                        self.updated = self.updated + 1
                    else:
                        self.debug_message("\t\t\t Page IS locked. Skipping Page save.")
                        self.skipped = self.skipped + 1
                else:
                    # Django model. Save normally.
                    self.debug_message("\t\t Saving Django model")
                    instance._skip_signals=True
                    instance.save()
                    self.updated = self.updated + 1

                # New record being processed. Save it to the list of records.
                self.records_used.append(record_id)
                # Object updated (and record was used)
                return True
            except ValidationError as error:
                self.skipped = self.skipped + 1
                error_message = "; ".join(error.messages)
                logger.error(
                    f"Unable to save {instance._meta.label} -> '{instance}'. Error(s): {error_message}"
                )
                self.debug_message(
                    f"\t\t Could not save Wagtail/Django model. Error: {error_message}"
                )
        else:
            logger.info(f"Invalid data for record {record_id}")
            self.debug_message(
                f"\t\t Serializer was invalid for record: {record_id}, model id: {instance.pk}"
            )
            self.debug_message(
                "\t\t Continuing to look for object by its unique identifier"
            )
        # Not updated.
        return False

    def update_object_by_uniq_col_name(
        self,
        field_mapping=None,
        model=None,
        serialized_data=None,
        record_id=None,
        is_wagtail_model=False,
    ):
        k, v = zip(*field_mapping.items())
        airtable_unique_identifier_field_name = k[0]
        unique_identifier = v[0]

        if unique_identifier:
            self.debug_message(
                f"\t\t An Airtable record based on the unique identifier was found: {airtable_unique_identifier_field_name}"
            )
            try:
                instance = model.objects.get(
                    **{airtable_unique_identifier_field_name: unique_identifier}
                )
                self.debug_message(
                    f"\t\t Local object found by Airtable unique column name: {airtable_unique_identifier_field_name}"
                )
            except model.DoesNotExist:
                instance = None
                self.debug_message(
                    "\t\t No object was found based on the Airtable column name"
                )

            if instance:
                # A local model object was found by a unique identifier.
                if serialized_data.is_valid():
                    for field_name, value in serialized_data.validated_data.items():
                        field_type = type(
                            model._meta.get_field(field_name)
                        )  # ie. django.db.models.fields.CharField
                        # If this field type is a subclass of a known Wagtail Tag, or a Django m2m field
                        # We need to loop through all the values and add them to the m2m-style field.
                        if issubclass(
                            field_type,
                            (
                                TaggableManager,
                                ClusterTaggableManager,
                                models.ManyToManyField,
                            ),
                        ):
                            m2m_field = getattr(instance, field_name)
                            for m2m_value in value:
                                m2m_field.add(m2m_value)
                        else:
                            setattr(instance, field_name, value)
                    # When an object is saved it should NOT push its newly saved data back to Airtable.
                    # This could theoretically cause a loop. By default this setting is False. But the
                    # below line confirms it's false, just to be safe.
                    instance.airtable_record_id = record_id
                    instance.push_to_airtable = False
                    try:
                        if is_wagtail_model:
                            # Wagtail page. Requires a .save_revision()
                            if not instance.locked:
                                # Only save the page if the page is not locked
                                instance._skip_signals=True
                                instance.save()
                                instance.save_revision()
                                self.updated = self.updated + 1
                            else:
                                self.debug_message(
                                    "\t\t\t Page IS locked. Skipping Page save."
                                )
                                self.skipped = self.skipped + 1
                        else:
                            # Django model. Save normally.
                            instance._skip_signals=True
                            instance.save()
                            self.debug_message("\t\t\t Saved!")
                            self.updated = self.updated + 1

                        # Record this record as "used"
                        self.records_used.append(record_id)
                        # New record being processed. Save it to the list of records.
                        return True
                    except ValidationError as error:
                        error_message = "; ".join(error.messages)
                        logger.error(
                            f"Unable to save {instance}. Error(s): {error_message}"
                        )
                        self.debug_message(
                            f"\t\t Unable to save {instance} (ID: {instance.pk}; Airtable Record ID: {record_id}). Reason: {error_message}"
                        )
                        self.skipped = self.skipped + 1
                else:
                    logger.info(f"Invalid data for record {record_id}")
                    self.debug_message("\t\t Serializer data was invalid.")
                    self.skipped = self.skipped + 1
            else:
                # No object was found by this unique ID.
                # Do nothing. The next step will be to create this object in Django
                logger.info(
                    f"{model._meta.verbose_name} with field {airtable_unique_identifier_field_name}={unique_identifier} was not found"
                )
                self.debug_message(
                    f"\t\t {model._meta.verbose_name} with field {airtable_unique_identifier_field_name}={unique_identifier} was not found"
                )
        else:
            # There was no unique identifier set for this model.
            # Nothing can be done about that right now.
            logger.info(f"{model._meta.verbose_name} does not have a unique identifier")
            self.debug_message(
                f"\t\t {model._meta.verbose_name} does not have a unique identifier"
            )
            self.skipped = self.skipped + 1
        return False

    def is_wagtail_page(self, model):
        if issubclass(model, Page):
            return True
        return False

    def get_data_for_new_model(self, serialized_data, mapped_import_fields, record_id):

        # Check if we can use the serialized data to create a new model.
        # If we can, great! If not, fall back to the original mapped_import_fields
        # If this has to fall back to the original mapped_import_fields: failure
        # to create a model will be higher than normal.
        if serialized_data.is_valid():
            data_for_new_model = dict(serialized_data.validated_data)
        else:
            data_for_new_model = mapped_import_fields
        data_for_new_model["airtable_record_id"] = record_id

        # First things first, remove any "pk" or "id" items from the mapped_import_fields
        # This will let Django and Wagtail handle the PK on its own, as it should.
        # When the model is saved it'll trigger a push to Airtable and automatically update
        # the necessary column with the new PK so it's always accurate.
        for key in (
            "pk",
            "id",
        ):
            try:
                del data_for_new_model[key]
            except KeyError:
                pass

        return data_for_new_model

    def run(self):

        models = get_validated_models(models=self.models)
        self.debug_message(f"Validated models: {models}")

        # Used for re-using API data instead of making several of API request and waiting/spamming the Airtable API
        # Maintain a list of record Ids that were used already. Every record is a unique ID so processing the
        # Same record more than once will just be hitting the DB over and over and over again. No bueno.

        for model in models:
            self.debug_message(f"IMPORTING MODEL: {model}")
            # Wagtail models require a .save_revision() call when being saved.
            is_wagtail_model = issubclass(model, Page)
            # Airtable global settings.
            airtable_settings = self.get_model_settings(model)

            # Set the unique identifier and serializer.
            model_serializer = self.get_model_serializer(
                airtable_settings.get("AIRTABLE_SERIALIZER")
            )
            # Get the unique column name and field name.
            # The CAN be the same value if a string is provided in the settings.
            (
                airtable_unique_identifier_column_name,
                airtable_unique_identifier_field_name,
            ) = self.get_column_to_field_names(
                airtable_settings.get("AIRTABLE_UNIQUE_IDENTIFIER")
            )

            if (
                not airtable_unique_identifier_field_name
                and not airtable_unique_identifier_column_name
            ):
                logger.error("No unique columns are set in your Airtable configuration")
                continue

            # Set the Airtable API client on a per-model basis
            if not TESTING:
                airtable = Airtable(
                    airtable_settings.get("AIRTABLE_BASE_KEY"),
                    airtable_settings.get("AIRTABLE_TABLE_NAME"),
                    api_key=settings.AIRTABLE_API_KEY,
                )
            else:
                airtable = MockAirtable(
                    airtable_settings.get("AIRTABLE_BASE_KEY"),
                    airtable_settings.get("AIRTABLE_TABLE_NAME"),
                    api_key=settings.AIRTABLE_API_KEY,
                )

            all_records = self.get_or_set_cached_records(airtable)

            self.debug_message(
                f"\t Airtable base key: {airtable_settings.get('AIRTABLE_BASE_KEY')}"
            )
            self.debug_message(
                f"\t Airtable table name: {airtable_settings.get('AIRTABLE_TABLE_NAME')}"
            )
            self.debug_message("\t Airtable unique identifier settings:")
            self.debug_message(f"\t Airtable records: {len(all_records)}")
            self.debug_message(
                f"\t\t Airtable column: {airtable_unique_identifier_column_name}"
            )
            self.debug_message(
                f"\t\t Django field name: {airtable_unique_identifier_field_name}"
            )

            # Loop through every record in the Airtable.
            for record in all_records:
                # If a record was used already, skip this iteration.
                if record["id"] in self.records_used:
                    continue


                record_id = record["id"]
                record_fields = record["fields"]
                mapped_import_fields = self.convert_mapped_fields(
                    record_fields, model.map_import_fields()
                )
                serialized_data = model_serializer(data=mapped_import_fields)
                serialized_data.is_valid()

                # Look for a record by its airtable_record_id.
                # If it exists, update the data.
                self.debug_message(
                    f"\n\t Looking for existing object with record: {record_id}"
                )
                try:
                    obj = model.objects.get(airtable_record_id=record_id)
                    self.debug_message(f"\t\t Local object found {obj}")
                except model.DoesNotExist:
                    obj = None
                    self.debug_message("\t\t Local object was NOT found")
                except model.MultipleObjectsReturned:
                    # In the case that multiple models have gotten the same record_id
                    objs = model.objects.filter(airtable_record_id=record_id)
                    # Set the first one to be the "right" one
                    obj = objs[0]
                    for ob in objs[1:]:
                        # set airtable_record_id on the "impostors" to ""
                        ob.airtable_record_id = ""
                        ob.save()


                if obj:
                    # Model object was found by it's airtable_record_id
                    was_updated = self.update_object(
                        instance=obj,
                        record_id=record_id,
                        serialized_data=serialized_data,
                        is_wagtail_model=is_wagtail_model,
                    )
                    # Object was updated. No need to continue through the rest of this function
                    if was_updated:
                        continue

                # This `unique_identifier` is the value of an Airtable record.
                # ie.
                #   fields = {
                #         'Slug': 'your-model'
                #   }
                # This will return 'your-model' and can now be searched for as model.objects.get(slug='your-model')
                unique_identifier = record_fields.get(
                    airtable_unique_identifier_column_name, None
                )
                was_updated = self.update_object_by_uniq_col_name(
                    field_mapping={
                        airtable_unique_identifier_field_name: unique_identifier
                    },
                    model=model,
                    serialized_data=serialized_data,
                    record_id=record_id,
                    is_wagtail_model=is_wagtail_model,
                )
                if was_updated:
                    continue

                # Look for the a PARENT_PAGE_ID setting and hopefully find a corresponding
                # Wagtail Page to set as the Parent Page. If the `parent_page` is set in
                # this conditional, it will be used later to create a new page.
                parent_page = None
                if self.is_wagtail_page(model):
                    # Page record was used. This is for caching duplicate entries to avoid too many API calls.
                    self.records_used.append(record_id)
                    self.debug_message("\t\t Checking PARENT_PAGE_ID settings...")

                    # Check if the PARENT_PAGE_ID setting is set. If it's not set in the Django settings,
                    # Don't try to create a new Wagtail Page.
                    parent_page_id_setting = airtable_settings.get("PARENT_PAGE_ID", None)
                    if parent_page_id_setting:
                        self.debug_message("\t\t Setting found...")

                        # Check if the PARENT_PAGE_ID is a callable, string location to a function, or an int ID.
                        if callable(parent_page_id_setting):
                            # A function was passed into the settings. Execute it.
                            parent_page_id = parent_page_id_setting()
                        elif isinstance(parent_page_id_setting, str):
                            # A string location was passed into the settings
                            # Parse the string function location and execute it
                            location, function_name = parent_page_id_setting.rsplit(".", 1)
                            module = import_module(location)
                            parent_page_callable = getattr(module, function_name)
                            parent_page_id = parent_page_callable()
                        else:
                            # This should be an integer representing the Parent Page to nest pages under
                            parent_page_id = parent_page_id_setting

                        try:
                            # Look for the parent page ID. If it doesn't exist, a page cannot be created.
                            # This needs to be set to a value for later use.
                            parent_page = Page.objects.get(pk=parent_page_id)
                        except Page.DoesNotExist:
                            logger.info(
                                f"Could not create new Page object. Parent page with ID {parent_page_id} doesn't exist"
                            )
                            self.debug_message(
                                f"\t\t Could not create new Page object. Parent page with ID {parent_page_id} doesn't exist"
                            )
                            continue

                # Attempt to format valid data to create a new model form either the
                # validated data in the serializer, or the mapped_field data.
                data_for_new_model = self.get_data_for_new_model(
                    serialized_data, mapped_import_fields, record_id
                )

                # If there is no match whatsoever, try to create a new `model` instance.
                # Note: this may fail if there isn't enough data in the Airtable record.
                try:
                    self.debug_message("\t\t Attempting to create a new Page...")
                    new_model = model(**data_for_new_model)
                    new_model._skip_signals=True
                    # `parent_page` is either None or a Page instance.
                    if parent_page:
                        # Pages are not live by default, and always have unpublished changes.
                        new_model.live = False
                        new_model.has_unpublished_changes = True

                        # Add the new page to the parent page.
                        parent_page.add_child(instance=new_model)

                        # If the settings are set to auto publish a page when it's imported,
                        # save the page revision and publish it. Otherwise just save the revision.
                        if airtable_settings.get("AUTO_PUBLISH_NEW_PAGES", False):
                            self.debug_message("\t\t Publishing new Page...")
                            new_model.save_revision().publish()
                        else:
                            new_model.save_revision()
                        self.debug_message("\t\t Page created")
                    else:
                        new_model.save()
                        self.debug_message("\t\t Object created")
                    self.created = self.created + 1
                except ValueError as value_error:
                    logger.info(
                        f"Could not create new model object. Value Error: {value_error}"
                    )
                    self.debug_message(
                        f"\t\t Could not create new model object. Value Error: {value_error}"
                    )
                except IntegrityError as e:
                    logger.info(
                        f"Could not create new model object. Integrity Error: {e}"
                    )
                    self.debug_message(
                        f"\t\t Could not create new model object. Integrity Error: {e}"
                    )
                except AttributeError as e:
                    logger.info(
                        f"Could not create new model object. AttributeError. Error: {e}"
                    )
                    self.debug_message(
                        f"\t\t Could not create new model object. AttributeError. Error: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"Unhandled error. Could not create a new object for {model._meta.verbose_name}. Error: {e}"
                    )
                    self.debug_message(
                        f"\t\t Unhandled error. Could not create a new object for {model._meta.verbose_name}. Error: {e}"
                    )

        return self.created, self.skipped, self.updated


class Command(BaseCommand):
    help = "Import data from an Airtable and overwrite model or page information"

    def add_arguments(self, parser):
        parser.add_argument(
            "labels",
            metavar="model_name",
            nargs="+",
            help="Model (as app_label.model_name) or app name to populate table entries for, e.g. creditcards.CreditCard",
        )

    def handle(self, *args, **options):
        """
        Runs the management command with the app_name.ModelName as parameters.
        ie. python manage.py import_airtable pages.HomePage creditcards.CreditCard

        This will handle Wagtail Pages (with page revisions) along with standard
        Django models.

        Models passed in to the command go through a quick validation to ensure they
        exist.

        Every model is then looped through, and a `settings.AIRTABLE_IMPORT_SETTINGS`
        is searched for based on the model's label (ie. pages.HomePage). These
        settings are used to connect to a certain Airtable Base (a set of spreadsheets),
        the name of the table to use, a unique identifier (used for connecting previously
        unrelated Airtable records to Django objects), and a serializer for validating
        incoming data from Airtable to make it work with the Django field types.

        Each model loop contains an `airtable.get_all()` command which
        will get all the data from the Airtable Table and load it into a
        list of dictionaries. This uses memoization to reduce memory hogging and
        wasted API calls to Airtable.

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
            AIRTABLE_DEBUG = getattr(settings, "WAGTAIL_AIRTABLE_DEBUG", False)
            if AIRTABLE_DEBUG:
                options["verbosity"] = 2

        importer = Importer(models=options["labels"], options=options)
        created, skipped, updated = importer.run()

        if options["verbosity"] >= 1:
            self.stdout.write(
                f"{created} object created. {updated} object updated. {skipped} object skipped."
            )

        # Use friendlier message. Slightly differs from the stdout.write() string.
        return f"{created} items created. {updated} items updated. {skipped} items skipped."
