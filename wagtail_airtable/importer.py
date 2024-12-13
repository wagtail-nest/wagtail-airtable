import logging
from airtable import Airtable
from django.conf import settings
from django.db.models.fields.related import ManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.managers import TaggableManager
from wagtail.models import Page
from .utils import import_string
from typing import NamedTuple, Optional
from django.db import transaction

logger = logging.getLogger(__name__)

class AirtableImportResult(NamedTuple):
    record_id: str
    fields: dict
    new: bool
    errors: Optional[dict] = None

    def error_display(self):
        """
        Show the errors in a human-readable way
        """
        if "exception" in self.errors:
            return repr(self.errors['exception'])
        # It's probably a DRF validation error
        output = ""
        for field_name, exceptions in sorted(self.errors.items()):
            output += f"{field_name}: "
            output += ", ".join([str(e).rstrip(".") for e in exceptions]) + ". "
        return output.strip()


def get_column_to_field_names(airtable_unique_identifier) -> tuple:
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


def convert_mapped_fields(record_fields_dict, mapped_fields_dict) -> dict:
    # Create a dictionary of newly mapped key:value pairs based on the `mappings` dict above.
    # This wil convert "airtable column name" to "django_field_name"
    mapped_fields_dict = {
        mapped_fields_dict[key]: value
        for (key, value) in record_fields_dict.items()
        if key in mapped_fields_dict
    }
    return mapped_fields_dict


def get_data_for_new_model(data, record_id):
    data_for_new_model = data.copy()
    data_for_new_model["airtable_record_id"] = record_id

    # First things first, remove any "pk" or "id" items from the mapped_import_fields
    # This will let Django and Wagtail handle the PK on its own, as it should.
    # When the model is saved it'll trigger a push to Airtable and automatically update
    # the necessary column with the new PK so it's always accurate.
    for key in {
        "pk",
        "id",
    }:
        try:
            del data_for_new_model[key]
        except KeyError:
            pass

    return data_for_new_model



class AirtableModelImporter:
    def __init__(self, model, verbosity=1):
        self.model = model
        self.model_settings = settings.AIRTABLE_IMPORT_SETTINGS[model._meta.label]
        self.model_is_page = issubclass(model, Page)
        self.model_serializer = import_string(self.model_settings["AIRTABLE_SERIALIZER"])

        if verbosity >= 2:
            logger.setLevel(logging.DEBUG)

        self.airtable_client = Airtable(
            self.model_settings.get("AIRTABLE_BASE_KEY"),
            self.model_settings.get("AIRTABLE_TABLE_NAME"),
            api_key=settings.AIRTABLE_API_KEY,
        )

        (
            self.airtable_unique_identifier_column_name,
            self.airtable_unique_identifier_field_name,
        ) = get_column_to_field_names(
            self.model_settings.get("AIRTABLE_UNIQUE_IDENTIFIER")
        )

        if not (
            self.airtable_unique_identifier_field_name and self.airtable_unique_identifier_column_name
        ):
            raise ValueError("No unique columns are set in your Airtable configuration")

        parent_page_id_setting = self.model_settings.get("PARENT_PAGE_ID", None)
        if parent_page_id_setting:
            if callable(parent_page_id_setting):
                # A function was passed into the settings. Execute it.
                parent_page_id = parent_page_id_setting()
            elif isinstance(parent_page_id_setting, str):
                parent_page_callable = import_string(parent_page_id_setting)
                parent_page_id = parent_page_callable()
            else:
                parent_page_id = parent_page_id_setting

            self.parent_page = Page.objects.get(pk=parent_page_id)
        else:
            self.parent_page = None

    def field_is_m2m(self, field_name):
        field_type = type(self.model._meta.get_field(field_name))

        return issubclass(
            field_type,
            (
                TaggableManager,
                ClusterTaggableManager,
                ManyToManyField,
            )
        )

    def update_object(self, instance, record_id, data):
        if self.model_is_page and instance.locked:
            logger.debug("Instance for %s is locked. Not updating.", record_id)
            return False

        if self.model_is_page:
            before = instance.to_json()

        for field_name, value in data.items():
            if self.field_is_m2m(field_name):
                # override existing values
                getattr(instance, field_name).set(value)
            else:
                setattr(instance, field_name, value)

        if self.model_is_page and before == instance.to_json():
            logger.debug("Instance %s didn't change, skipping save.", record_id)
            return False

        # When an object is saved it should NOT push its newly saved data back to Airtable.
        # This could theoretically cause a loop. By default this setting is False. But the
        # below line confirms it's false, just to be safe.
        instance.push_to_airtable = False

        instance.airtable_record_id = record_id
        instance._skip_signals = True
        instance.save()
        if self.model_is_page:
            # When saving a page, create it as a new revision
            instance.save_revision()
        return True

    def create_object(self, data, record_id):
        data_for_new_model = get_data_for_new_model(data, record_id)

        # extract m2m fields to avoid getting the error
        # "direct assignment to the forward side of a many-to-many set is prohibited"
        m2m_data = {}
        non_m2m_data = {}
        for field_name, value in data_for_new_model.items():
            if self.field_is_m2m(field_name):
                m2m_data[field_name] = value
            else:
                non_m2m_data[field_name] = value

        new_model = self.model(**non_m2m_data)
        new_model._skip_signals = True
        new_model.push_to_airtable = False

        if self.parent_page:
            new_model.live = False
            new_model.has_unpublished_changes = True

            self.parent_page.add_child(instance=new_model)

            # If the settings are set to auto publish a page when it's imported,
            # save the page revision and publish it. Otherwise just save the revision.
            if self.model_settings.get("AUTO_PUBLISH_NEW_PAGES", False):
                new_model.save_revision().publish()
            else:
                new_model.save_revision()
        else:
            new_model.save()
            for field_name, value in m2m_data.items():
                getattr(new_model, field_name).set(value)

    def get_existing_instance(self, record_id, unique_identifier):
        existing_by_record_id = self.model.objects.filter(airtable_record_id=record_id).first()
        if existing_by_record_id is not None:
            logger.debug("Found existing instance by id: %s", existing_by_record_id.id)
            return existing_by_record_id

        existing_by_unique_identifier = self.model.objects.filter(
            **{self.airtable_unique_identifier_field_name: unique_identifier}
        ).first()
        if existing_by_unique_identifier is not None:
            logger.debug("Found existing instance by unique identifier: %s", existing_by_unique_identifier.id)
            return existing_by_unique_identifier

        # Couldn't find an instance
        return None

    @transaction.atomic
    def process_record(self, record):
        record_id = record['id']
        fields = record["fields"]

        mapped_import_fields = convert_mapped_fields(
            fields, self.model.map_import_fields()
        )

        unique_identifier = fields.get(
            self.airtable_unique_identifier_column_name, None
        )
        obj = self.get_existing_instance(record_id, unique_identifier)

        logger.debug("Validating data for %s", record_id)
        serializer = self.model_serializer(data=mapped_import_fields)

        if not serializer.is_valid():
            return AirtableImportResult(record_id, fields, errors=serializer.errors, new=obj is not None)

        if obj:
            logger.debug("Attempting update of %s", obj.id)
            try:
                was_updated = self.update_object(
                    instance=obj,
                    record_id=record_id,
                    data=serializer.validated_data,
                )
            except Exception as e:  # noqa: B902
                return AirtableImportResult(record_id, fields, new=False, errors={"exception": e})
            if was_updated:
                logger.debug("Updated instance for %s", record_id)
            else:
                logger.debug("Skipped update for %s", record_id)
            return AirtableImportResult(record_id, fields, new=False)
        else:
            logger.debug("Creating model for %s", record_id)
            try:
                self.create_object(serializer.validated_data, record_id)
            except Exception as e:  # noqa: B902
                return AirtableImportResult(record_id, fields, new=True, errors={"exception": e})
            logger.debug("Created instance for %s", record_id)
            return AirtableImportResult(record_id, fields, new=True)

    def run(self):
        for page in self.airtable_client.get_iter():
            for record in page:
                logger.info("Processing record %s", record["id"])
                yield self.process_record(record)
