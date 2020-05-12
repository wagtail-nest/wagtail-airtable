from django.conf import settings
from django.conf.urls import url
from django.contrib import messages
from django.urls import reverse
from wagtail.core import hooks
from wagtail.admin.menu import MenuItem

from wagtail_airtable.views import AirtableImportListing
from .mixins import AirtableMixin

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


@hooks.register('after_edit_page')
def after_page_update(request, page):
    # Check if the page is an AirtableMixin Subclass
    if settings.WAGTAIL_AIRTABLE_ENABLED and issubclass(page.__class__, AirtableMixin):
        # When AirtableMixin.save() is called..
        # Either it'll connect with Airtable and update the row as expected, or
        # it will have some type of error.
        # If _airtable_update_error exists on the page, use that string as the
        # message error.
        # Otherwise assume a successful update happened on the Airtable row
        if hasattr(page, '_airtable_update_error'):
            messages.add_message(request, messages.ERROR, page._airtable_update_error)
        else:
            messages.add_message(request, messages.SUCCESS, "Airtable record updated")


@hooks.register('after_edit_snippet')
def after_snippet_update(request, instance):
    if settings.WAGTAIL_AIRTABLE_ENABLED and issubclass(instance.__class__, AirtableMixin):
        # When AirtableMixin.save() is called..
        # Either it'll connect with Airtable and update the row as expected, or
        # it will have some type of error.
        # If _airtable_update_error exists on the page, use that string as the
        # message error.
        # Otherwise assume a successful update happened on the Airtable row
        if hasattr(instance, '_airtable_update_error'):
            messages.add_message(request, messages.ERROR, instance._airtable_update_error)
        else:
            messages.add_message(request, messages.SUCCESS, "Airtable record updated")
