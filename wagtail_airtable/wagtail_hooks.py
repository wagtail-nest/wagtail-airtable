from django.conf import settings
from django.conf.urls import url
from django.urls import reverse
from wagtail.core import hooks
from wagtail.admin.menu import MenuItem

from wagtail_airtable.views import AirtableImportListing
from wagtail_airtable.utils import airtable_message, can_send_airtable_messages
from .mixins import AirtableMixin


@hooks.register("register_admin_urls")
def register_airtable_url():
    return [
        url(
            r"^airtable-import/$",
            AirtableImportListing.as_view(),
            name="airtable_import_listing",
        ),
    ]


@hooks.register("register_settings_menu_item")
def register_airtable_setting():
    def is_shown(request):
        return getattr(settings, "WAGTAIL_AIRTABLE_ENABLED", False)

    menu_item = MenuItem(
        "Airtable Import",
        reverse("airtable_import_listing"),
        classnames="icon icon-cog",
        order=1000,
    )
    menu_item.is_shown = is_shown
    return menu_item


@hooks.register("after_edit_page")
def after_page_update(request, page):
    if can_send_airtable_messages(page):
        airtable_message(request, page)


@hooks.register("after_create_snippet")
@hooks.register("after_edit_snippet")
def after_snippet_update(request, instance):
    if can_send_airtable_messages(instance):
        airtable_message(request, instance)


@hooks.register("after_delete_snippet")
def after_snippet_delete(request, instances):
    total_deleted = len(instances)
    instance = instances[0]
    if can_send_airtable_messages(instance):
        message = f"Airtable record deleted"
        if total_deleted > 1:
            message = f"{total_deleted} Airtable records deleted"
        airtable_message(request, instance, message=message, buttons_enabled=False)
