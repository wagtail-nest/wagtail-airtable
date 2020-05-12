from django.conf import settings
from django.conf.urls import url
from django.urls import reverse
from wagtail.core import hooks
from wagtail.admin.menu import MenuItem

from wagtail_airtable.views import AirtableImportListing


@hooks.register('register_admin_urls')
def register_airtable_url():
    return [
        url(r'^airtable-import/$', AirtableImportListing.as_view(), name='airtable_import_listing'),
    ]


@hooks.register("register_settings_menu_item")
def register_airtable_setting():

    def is_shown(request):
        return settings.WAGTAIL_AIRTABLE_ENABLED

    menu_item = MenuItem(
        "Airtable Import",
        reverse("airtable_import_listing"),
        classnames="icon icon-cog",
        order=1000,
    )
    menu_item.is_shown = is_shown
    return menu_item
