from django.db import models

from wagtail_airtable.mixins import AirtableMixin


class YourModel(AirtableMixin, models.Model):

    name = models.CharField(max_length=200, blank=False)
    slug = models.SlugField(max_length=200, unique=True, editable=True)

    @classmethod
    def map_import_fields(cls, incoming_dict_fields={}):
        """
        Maps your Airtable columns to your Django Model Fields.

        Always provide explicit field names as to not accidentally overwrite sensitive information
        such as model pk's.

        Return a dictionary such as: {'Airtable column name': 'model_field_name', ...}
        """
        mappings = {
            # "Name" is the column name in Airtable. "name" (lowercase) is the field name on line 8.
            "Name": "name",
            # "Slug" is the column name in Airtable. "slug" (lowercase) is the field name on line 8.
            "Slug": "slug",
        }

        # Create a dictionary of newly mapped key:value pairs based on the `mappings` dict above.
        # ie. This wil convert "airtable column name" to "django_field_name"
        # TODO Put this into the airtable package
        return_dict = {
            mappings[key]: value for (key, value) in incoming_dict_fields.items() if key in mappings
        }

        return return_dict

    def get_export_fields(self):
        """
        Export fields are the fields you want to map when saving a model object.

        Everytime a model is saved, it will take the Airtable Column Name and fill the appropriate cell
        with the data you tell it. Most often this will be from self.your_field_name.

        Always provide explicit field names as to not accidentally share sensitive information such as
        hashed passwords.

        Return a dictionary such as: {"Airtable Column Name": "update_value", ...}
        """
        return {
            "Name": self.name,
            "Slug": self.slug,
        }
