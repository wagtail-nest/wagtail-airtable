import sys
from ast import literal_eval
from logging import getLogger

from airtable import Airtable
from django.conf import settings
from django.db import models
from requests import HTTPError

from django.utils.functional import cached_property

from .tests import MockAirtable

logger = getLogger(__name__)


TESTING = any(x in ["test", "runtests.py"] for x in sys.argv)


class AirtableMixin(models.Model):
    """A mixin to update an Airtable when a model object is saved or deleted."""

    AIRTABLE_BASE_KEY = None
    AIRTABLE_TABLE_NAME = None
    AIRTABLE_UNIQUE_IDENTIFIER = None

    # On import, a lot of saving happens, so this attribute gets set to True during import and could be
    # used as a bit of logic to skip a post_save signal, for example.
    _skip_signals = False
    # If the Airtable integration for this model is enabled. Used for sending data to Airtable.
    _is_enabled = False
    # If the Airtable api setup is complete in this model. Used for singleton-like setup_airtable() method.
    _ran_airtable_setup = False
    # Upon save, should this model's data be sent to Airtable?
    # This is an internal variable. Both _push_to_airtable and push_to_airtable needs to be True
    # before a push to Airtable will happen.
    # _push_to_airtable is for internal use only
    _push_to_airtable = False
    # Case for disabling this: when importing data from Airtable as to not
    # ... import data, save the model, and push the same data back to Airtable.
    # push_to_airtable can be set from outside the model
    push_to_airtable = True

    airtable_record_id = models.CharField(max_length=35, db_index=True, blank=True)

    def setup_airtable(self) -> None:
        """
        This method is used in place of __init__() as to not check global settings and
        set the Airtable api client over and over again.

        self._ran_airtable_setup is used to ensure this method is only ever run once.
        """
        if not self._ran_airtable_setup:
            # Don't run this more than once on a model.
            self._ran_airtable_setup = True

            if not hasattr(settings, "AIRTABLE_IMPORT_SETTINGS") or not getattr(
                settings, "WAGTAIL_AIRTABLE_ENABLED", False
            ):
                # No AIRTABLE_IMPORT_SETTINGS were found. Skip checking for settings.
                return None

            # Look for airtable settings. Default to an empty dict.
            AIRTABLE_SETTINGS = settings.AIRTABLE_IMPORT_SETTINGS.get(
                self._meta.label, {}
            )

            self.AIRTABLE_BASE_URL = AIRTABLE_SETTINGS.get("AIRTABLE_BASE_URL", None)
            # Set the airtable settings.
            self.AIRTABLE_BASE_KEY = AIRTABLE_SETTINGS.get("AIRTABLE_BASE_KEY")
            self.AIRTABLE_TABLE_NAME = AIRTABLE_SETTINGS.get("AIRTABLE_TABLE_NAME")
            self.AIRTABLE_UNIQUE_IDENTIFIER = AIRTABLE_SETTINGS.get(
                "AIRTABLE_UNIQUE_IDENTIFIER"
            )
            self.AIRTABLE_SERIALIZER = AIRTABLE_SETTINGS.get("AIRTABLE_SERIALIZER")
            if (
                AIRTABLE_SETTINGS
                and settings.AIRTABLE_API_KEY
                and self.AIRTABLE_BASE_KEY
                and self.AIRTABLE_TABLE_NAME
                and self.AIRTABLE_UNIQUE_IDENTIFIER
            ):
                if not TESTING:
                    self.client = Airtable(
                        self.AIRTABLE_BASE_KEY,
                        self.AIRTABLE_TABLE_NAME,
                        api_key=settings.AIRTABLE_API_KEY,
                    )
                else:
                    self.client = MockAirtable(
                        self.AIRTABLE_BASE_KEY,
                        self.AIRTABLE_TABLE_NAME,
                        api_key=settings.AIRTABLE_API_KEY,
                    )

                self._push_to_airtable = True
                self._is_enabled = True
            else:
                logger.warning(
                    f"Airtable settings are not enabled for the {self._meta.verbose_name} "
                    f"({self._meta.model_name}) model"
                )

    def get_record_usage_url(self):
        if self.is_airtable_enabled and self.AIRTABLE_BASE_URL and self.airtable_record_id:
            url = self.AIRTABLE_BASE_URL.rstrip('/')
            return f"{url}/{self.airtable_record_id}"
        return None

    @property
    def is_airtable_enabled(self):
        """
        Used in the template to determine if a model can or cannot be imported from Airtable.
        """
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

    def create_record(self) -> dict:
        """
        Create or update a record.

        The create_record() method will look for an Airtable match before trying
        to create a new Airtable record (that comes with a new airtable_record_id).

        This function needs to check for a matched record in Airtable first just in case
        some data became out of sync, or one person worked in Airtable and one worked in
        Wagtail. The idea here is to marry those records whenever possible instead of
        duplicating Airtable records.

        If a record in Airtable exists, update this object with the found record_id. (Prevent record duplication)
        But if a record is NOT found in Airtable, create a new record.
        """
        matched_record = self.match_record()
        if matched_record:
            record = self.update_record(matched_record)
        else:
            record = self.client.insert(self.mapped_export_fields)

        self.airtable_record_id = record["id"]
        return record

    def check_record_exists(self, airtable_record_id) -> bool:
        """
        Check if a record exists in an Airtable by its exact Airtable Record ID.

        This will trigger an Airtable API request.
        Returns a True/False response.
        """
        try:
            record = self.client.get(airtable_record_id)
        except HTTPError:
            record = {}
        return bool(record)

    def update_record(self, airtable_record_id=None):
        """
        Update a record.

        Before updating a record this will check to see if a record even exists
        in Airtable. If a record is not found using its Airtable record_id it cannot
        be updated and may throw an unexpected error.

        If a record DOES exist based on its Airtable record_id, we can update that particular row.
        If a record does NOT exist in Airtable, a new record will need to be created.
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
        """
        Deletes a record from Airtable, but does not delete the object from Django.

        Returns True if the record is successfully deleted, otherwise False.
        """
        try:
            response = self.client.delete(self.airtable_record_id)
            deleted = response["deleted"]
        except HTTPError:
            deleted = False
        return deleted

    def match_record(self) -> str:
        """
        Look for a record in an Airtable. Search by the AIRTABLE_UNIQUE_IDENTIFIER.

        Instead of looking for an Airtable record by it's exact Record ID, it will
        search through the specified Airtable column for a specific value.

        WARNING: If more than one record is found, the first one in the returned
        list of records (a list of dicts) will be used.

        This differs from check_record_exists() as this will return the record string
        (or an empty string if a record is not found), whereas check_record_exists()
        will return a True/False boolean to let you know if a record simply exists,
        or doesn't exist.
        """
        if type(self.AIRTABLE_UNIQUE_IDENTIFIER) == dict:
            keys = list(self.AIRTABLE_UNIQUE_IDENTIFIER.keys())
            values = list(self.AIRTABLE_UNIQUE_IDENTIFIER.values())
            # TODO: Edge case handling:
            #       - Handle multiple dictionary keys
            #       - Handle empty dictionary
            airtable_column_name = keys[0]
            model_field_name = values[0]
            value = getattr(self, model_field_name)
        else:
            _airtable_unique_identifier = self.AIRTABLE_UNIQUE_IDENTIFIER
            value = getattr(self, _airtable_unique_identifier)
            airtable_column_name = self.AIRTABLE_UNIQUE_IDENTIFIER
        records = self.client.search(airtable_column_name, value)
        total_records = len(records)
        if total_records:
            # If more than 1 record was returned log a warning.
            if total_records > 1:
                logger.info(
                    f"Found {total_records} Airtable records for {airtable_column_name}={value}. "
                    f"Using first available record ({records[0]['id']}) and ignoring the others."
                )
            # Always return the first record
            return records[0]["id"]

        return ""

    def refresh_mapped_export_fields(self) -> None:
        """Delete the @cached_property caching on self.mapped_export_fields."""
        try:
            del self.mapped_export_fields
        except Exception:
            # Doesn't matter what the error is.
            pass

    @classmethod
    def parse_request_error(cls, error):
        """
        Parse an Airtable/requests HTTPError string.

        Example: 401 Client Error: Unauthorized for url: https://api.airtable.com/v0/appYourAppId/Your%20Table?filterByFormula=.... [Error: {'type': 'AUTHENTICATION_REQUIRED', 'message': 'Authentication required'}]
        Example: 503 Server Error: Service Unavailable for url: https://api.airtable.com/v0/appXXXXXXXX/BaseName'
        """
        if not error or "503 Server Error" in error:
            # If there is a 503 error
            return {
                "status_code": 503,
                "type": "SERVICE_UNAVAILABLE",
                "message": "Airtable may be down, or is otherwise unreachable"
            }

        code = int(error.split(":", 1)[0].split(" ")[0])
        if code == 502:
            # If there is a 502 error
            return {
                "status_code": code,
                "type": "SERVER_ERROR",
                "message": "Service may be down, or is otherwise unreachable"
            }

        error_json = error.split("[Error: ")[1].rstrip("]")
        if error_json == "NOT_FOUND":  # 404's act different
            return {
                "status_code": code,
                "type": "NOT_FOUND",
                "message": "Record not found",
            }
        else:
            error_info = literal_eval(error_json)
            return {
                "status_code": code,
                "type": error_info["type"],
                "message": error_info["message"],
            }

    def save(self, *args, **kwargs):
        """
        If there's an existing airtable record id, update the row.
        Otherwise attempt to create a new record.
        """
        saved_model = super().save(*args, **kwargs) # Save to database first so we get pk, in case it's used for uniqueness
        self.setup_airtable()
        if self._push_to_airtable and self.push_to_airtable:
            # Every airtable model needs mapped fields.
            # mapped_export_fields is a cached property. Delete the cached prop and get new values upon save.
            self.refresh_mapped_export_fields()
            if self.airtable_record_id:
                # If this model has an airtable_record_id, attempt to update the record.
                try:
                    self.update_record()
                except HTTPError as e:
                    error = self.parse_request_error(e.args[0])
                    message = (
                        f"Could not update Airtable record. Reason: {error['message']}"
                    )
                    logger.warning(message)
                    # Used in the `after_edit_page` hook. If it exists, an error message will be displayed.
                    self._airtable_update_error = message
            else:
                # Creating a record will also search for an existing field match
                # ie. Looks for a matching `slug` in Airtable and Wagtail/Django
                try:
                    self.create_record()
                    # Save once more so the airtable_record_id is stored.
                    super().save(*args, **kwargs)
                except HTTPError as e:
                    error = self.parse_request_error(e.args[0])
                    message = (
                        f"Could not create Airtable record. Reason: {error['message']}"
                    )
                    logger.warning(message)
                    # Used in the `after_edit_page` hook. If it exists, an error message will be displayed.
                    self._airtable_update_error = message

        return saved_model

    def delete(self, *args, **kwargs):
        self.setup_airtable()
        if self.push_to_airtable and self._push_to_airtable and self.airtable_record_id:
            # Try to delete the record from the Airtable.
            self.delete_record()
        return super().delete(*args, **kwargs)

    class Meta:
        abstract = True
