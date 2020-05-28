from django.test import TestCase

from wagtail_airtable.templatetags.wagtail_airtable_tags import can_import_model


class TestTemplateTags(TestCase):

    def test_can_import_model(self):
        allowed_to_import = can_import_model("tests.Advert")
        self.assertTrue(allowed_to_import)

    def test_cannot_import_model(self):
        allowed_to_import = can_import_model("tests.MissingModel")
        self.assertFalse(allowed_to_import)
