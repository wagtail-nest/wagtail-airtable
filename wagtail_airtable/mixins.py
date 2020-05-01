from importlib import import_module
from logging import getLogger

from airtable import Airtable
from django.conf import settings
from django.db import models

from django.utils.functional import cached_property

logger = getLogger(__name__)


class AirtableMixin(models.Model):
    """A mixin to update an Airtable when a model object is saved or deleted."""

    AIRTABLE_BASE_KEY = None
    AIRTABLE_TABLE_NAME = None
    AIRTABLE_UNIQUE_IDENTIFIER = None

    # If the Airtable integration for this model is enabled. Used for sending data to Airtable.
    _is_enabled = False
    # If the Airtable api setup is complete in this model. Used for singleton-like setup_airtable() method.
    _ran_airtable_setup = False
    # Upon save, should this models data be sent to Airtable?
    # Case for disabling this: when importing data from Airtable as to not
    # ... import data, save the model, and push the same data back to Airtable.
    push_to_airtable = True

    airtable_record_id = models.CharField(max_length=35, db_index=True, blank=True)

    def _find_adjacent_models(self) -> dict:
        # If a base setting for a specified model or Page is not immediately found in the
        # settings (ie. settings.AIRTABLE_IMPORT_SETTINGS keys)
        # we will need to loop through each set of dictionaries, look for `EXTRA_SUPPORTED_MODELS`
        # and if it exists check to see if the current model is in the `EXTRA_SUPPORTED_MODELS` list
        for model_path, model_settings in settings.AIRTABLE_IMPORT_SETTINGS.items():
            # `EXTRA_SUPPORTED_MODELS` is an optional setting and may not exist.
            if model_settings.get('EXTRA_SUPPORTED_MODELS'):
                # Always convert `EXTRA_SUPPORTED_MODELS` to a list for iteration.
                # Then loop through every model in the list and covert it to lowercase
                # so we can compare the current models label (lowercase) to a list of lowercased models
                _list_of_models = list(model_settings.get('EXTRA_SUPPORTED_MODELS', []))
                _extra_supported_models = [_model.lower() for _model in _list_of_models]
                # Check that self._meta.label_lower is in the list of `EXTRA_SUPPORTED_MODELS`
                # (all lowercased for proper string matching)
                if self._meta.label_lower in _extra_supported_models:
                    return settings.AIRTABLE_IMPORT_SETTINGS[model_path]
        return {}

    def setup_airtable(self) -> None:
        """
        This method is used in place of __init__() as to not check global settings and
        set the Airtable api client over and over again.

        self._ran_airtable_setup is used to ensure this method is only ever run once.
        """
        if not self._ran_airtable_setup:

            self._ran_airtable_setup = True
            # Look for airtable settings. Default to an empty dict.
            AIRTABLE_SETTINGS = settings.AIRTABLE_IMPORT_SETTINGS.get(self._meta.label, {})

            if not AIRTABLE_SETTINGS:
                AIRTABLE_SETTINGS = self._find_adjacent_models()

            # Set the airtable settings.
            self.AIRTABLE_BASE_KEY = AIRTABLE_SETTINGS.get('AIRTABLE_BASE_KEY')
            self.AIRTABLE_TABLE_NAME = AIRTABLE_SETTINGS.get('AIRTABLE_TABLE_NAME')
            self.AIRTABLE_UNIQUE_IDENTIFIER = AIRTABLE_SETTINGS.get('AIRTABLE_UNIQUE_IDENTIFIER')
            self.AIRTABLE_SERIALIZER = AIRTABLE_SETTINGS.get('AIRTABLE_SERIALIZER')
            if (
                AIRTABLE_SETTINGS
                and settings.AIRTABLE_API_KEY
                and self.AIRTABLE_BASE_KEY
                and self.AIRTABLE_TABLE_NAME
                and self.AIRTABLE_UNIQUE_IDENTIFIER
            ):
                self.client = Airtable(
                    self.AIRTABLE_BASE_KEY,
                    self.AIRTABLE_TABLE_NAME,
                    api_key=settings.AIRTABLE_API_KEY,
                )
                self._is_enabled = True
            else:
                logger.warning(
                    f"Airtable settings are not enabled for the {self._meta.verbose_name} "
                    f"({self._meta.model_name}) model"
                )

    @property
    def is_airtable_enabled(self):
        if not self._ran_airtable_setup:
            self.setup_airtable()
        return self._is_enabled

    def get_import_fields(self):
        """
        When implemented, should return a dictionary of the mapped fields from Airtable to the model.
        ie.
            {
                "Airtable Column Name": "model_field_name",
                ...
            }
        """
        raise NotImplementedError

    def get_export_fields(self):
        """
        When implemented, should return a dictionary of the mapped fields from Airtable to the model.
        ie.
            {
                "airtable_column": self.airtable_column,
                "annual_fee": self.annual_fee,
            }
        """
        raise NotImplementedError

    @cached_property
    def mapped_export_fields(self):
        return self.get_export_fields()

    def create_record(self):
        """
        Create or update a record.

        Because a new Airtable record might already exist in Airtable,
        this method will need to attempt to match a unique record by a unique value in an Airtable column.
        If a value is found in Airtable, use that records ID and update that column.
        """
        matched_record = self.match_record()
        if matched_record:
            record = self.update_record(matched_record)
        else:
            record = self.client.insert(self.mapped_export_fields)

        self.airtable_record_id = record["id"]
        return record

    def check_record_exists(self, airtable_record_id) -> bool:
        """Check if a record exists in an Airtable."""
        try:
            record = self.client.get(airtable_record_id)
        except HTTPError:
            record = {}
        return bool(record)

    def update_record(self, airtable_record_id=None):
        """
        Update a record.

        If a record exists, it will update it.
        If a record does not exist, it will call self.create_record()
        """
        airtable_record_id = airtable_record_id or self.airtable_record_id

        if self.check_record_exists(airtable_record_id):
            # Record exists in Airtable
            record = self.client.update(airtable_record_id, self.mapped_export_fields)
        else:
            # No record exists in Airtable. Create a new record now.
            record = self.create_record()

        self.airtable_record_id = record["id"]
        return record

    def delete_record(self) -> bool:
        """Delete a record. Return True/False."""
        try:
            response = self.client.delete(self.airtable_record_id)
            deleted = response["deleted"]
        except HTTPError:
            deleted = False
        return deleted

    def match_record(self) -> str:
        """Look for a record in an Airtable. Search by the AIRTABLE_UNIQUE_IDENTIFIER."""

        if type(self.AIRTABLE_UNIQUE_IDENTIFIER) == dict:
            keys = list(self.AIRTABLE_UNIQUE_IDENTIFIER.keys())
            values = list(self.AIRTABLE_UNIQUE_IDENTIFIER.values())
            airtable_column_name = keys[0]
            model_field_name = values[0]
            value = getattr(self, model_field_name)
            records = self.client.search(airtable_column_name, value)
            if len(records) == 1:
                # Only one record to return.
                # TODO Handle more than one result from the airtable.seach() method
                return records[0]["id"]
        else:
            _airtable_unique_identifier = self.AIRTABLE_UNIQUE_IDENTIFIER
            value = getattr(self, _airtable_unique_identifier)
            records = self.client.search(self.AIRTABLE_UNIQUE_IDENTIFIER, value)
            if len(records) == 1:
                # Only one record to return.
                # TODO Handle more than one result from the airtable.seach() method
                return records[0]["id"]
        return ""

    def refresh_mapped_export_fields(self) -> None:
        """Delete the @cached_property caching on self.mapped_export_fields."""
        try:
            del self.mapped_export_fields
        except Exception as e:
            pass

    def save(self, *args, **kwargs):
        """
        If there's an existing airtable record id, update the row.
        Otherwise attempt to create a new record.
        """
        save = super().save(*args, **kwargs)
        self.setup_airtable()
        if self._is_enabled and getattr(settings, "WAGTAIL_AIRTABLE_ENABLED", False) and self.push_to_airtable:
            # Every airtable model needs mapped fields.
            # mapped_export_fields is a cached property. Delete the cached prop and get new values upon save.
            self.refresh_mapped_export_fields()
            if self.airtable_record_id:
                # If this model has an airtable_record_id, attempt to update the record.
                self.update_record()
            else:
                # Creating a record will also search for an existing field match
                # ie. Looks for a matching `slug` in Airtable and Wagtail/Django
                self.create_record()
            super().save(*args, **kwargs)
        return save

    def delete(self, *args, **kwargs):
        self.setup_airtable()
        if self.airtable_record_id:
            # Try to delete the record from the Air Table.
            self.delete_record()
        return super().delete(*args, **kwargs)

    class Meta:
        abstract = True
