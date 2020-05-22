from django.db import models
from django.utils import timezone

from wagtail.core.models import Page
from wagtail_airtable.mixins import AirtableMixin


class HomePage(AirtableMixin, Page):

    # Wagtail stuff..
    parent_page_types = ["wagtailcore.page"]
    template = ["templates/home_page.html"]

    # Custom fields
    name = models.CharField(max_length=200, blank=False)
    total_awesomeness = models.DecimalField(
        blank=True, null=True, decimal_places=1, max_digits=2
    )

    # Custom property or methods allowed when exporting
    # There is no custom property/method support when importing from Airtable because it won't know
    # where to map the data to since custom properties and methods are not stored fields.
    @property
    def top_rated_page(self):
        if self.total_awesomeness >= 80:
            return True
        return False

    @classmethod
    def map_import_fields(cls):
        """
        Maps your Airtable columns to your Django Model Fields.

        Always provide explicit field names as to not accidentally overwrite sensitive information
        such as model pk's.

        Return a dictionary such as:
            {
                'Name': 'title',
                'Awesomeness Rating': 'total_awesomeness',
                'Other Airtable Column Name': 'your_django_or_wagtail_field_name',
            }
        """
        mappings = {
            # "Name" is the column name in Airtable. "title" (lowercase) is the field name on line 26.
            "Name": "title",
            # "Slug" is the column name in Airtable. "slug" (lowercase) comes from Page.slug.
            # I've kept "slug" commented out so Airtable cannot overwrite the Page slug as that could cause a lot of trouble with URLs and SEO. But it's possible to do this assuming there aren't two pages with the same slug.
            # "Slug": "slug",
            "Awesomeness Rating": "total_awesomeness",
            "Last Updated": "last_published_at",
        }
        return mappings

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
            "Slug": self.slug,  # `slug` is a field found on Page that comes with Wagtail
            "Awesomeness Rating": str(self.total_awesomeness)
            if self.total_awesomeness
            else None,  # Send the Decimal as a string.
            "Top Rated Awesomeness": self.top_rated_page,  # Must be a checkbox column in Airtable.
            # If a cell in Airtable should always be filled, but the data might be optional at some point
            # You can use a function, method, custom property or ternary operator to set the defaults.
            "Last Updated": self.last_published_at
            if self.last_published_at
            else timezone.now().isoformat(),
        }

    class Meta:
        verbose_name = "The Best HomePage Ever"
