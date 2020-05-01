from django.db import models
from django.utils import timezone

from wagtail.core.models import Page
from wagtail_airtable.mixins import AirtableMixin


class BasePage(AirtableMixin, Page):
    """
    This is using the AirtableMixin and the Wagtail Page model to create a new
    "BasePage" model. Then new Pages are created using the "BasePage model
    they will automatically inherit the import/export field mapping you see
    below.

    When using multi model inheritance you can use the
    optional `EXTRA_SUPPORTED_MODELS` setting. See settings.py for the
    relevant settings

    Note: You'll most likely want BasePage to be an Abstract Model.
    """
    @classmethod
    def map_import_fields(cls, incoming_dict_fields={}):
        """
        Fields to update when importing a specific page.
        These are just updating the seo_title, title, and search_description
        fields that come with wagtailcore.Page.

        NOTE: Unless you store required data like the page depth or tree value
        in Airtable, when you import a new page it won't be automatically created.
        Wagtail doesn't know where you'd like new pages to be created but requires
        tree-structure data.

        Example:
            {'Airtable column name': 'model_field_name', ...}
        """

        return {
            "SEO Title": "seo_title",
            "Title": "title",
            "Meta Description": "search_description",
        }

    def get_export_fields(self):
        """
        Map Airtable columns to values from Wagtail or Django.

        Example:
            {'Airtable Column Name': updated_value, ...}
        """
        return {
            "SEO Title": self.seo_title,
            "Title": self.title,
            "URL": self.full_url,
            "Last Published": self.last_published_at.isoformat() if self.last_published_at else '',
            "Meta Description": self.search_description,
            "Type": self.__class__.__name__,
            "Live": self.live,
            "Unpublished Changes": self.has_unpublished_changes,
            "Wagtail Page ID": self.id,
            "Slug": self.slug,
        }

    class Meta:
        abstract = True


class HomePage2(BasePage):
    pass


class ContactPage(BasePage):
    pass


class BlogPage(BasePage):
    pass


class MiscPage(BasePage):
    pass
