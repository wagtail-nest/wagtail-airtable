from copy import copy
from unittest import mock

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.test import TestCase

from wagtail_airtable.management.commands.import_airtable import Importer
from wagtail_airtable.tests import MockAirtable
from tests.models import Advert, ModelNotUsed, SimilarToAdvert, SimplePage
from tests.serializers import AdvertSerializer


# TODO: Add import tests
class TestImportClass(TestCase):

    def setUp(self):
        self.options = {
            'verbosity': 2
        }

    def test_debug_message(self):
        models = ["fake.ModelName"]
        text = "Testing debug message with high verbosity"

        # Default verbosity
        importer = Importer(models=models)
        debug_message = importer.debug_message(text)
        self.assertEqual(debug_message, text)

        # Lower verbosity
        importer = Importer(models=models, options={'verbosity': 1})
        debug_message = importer.debug_message(text)
        self.assertEqual(debug_message, None)

    def test_get_validated_models_with_invalid_model(self):
        models = ["fake.ModelName"]
        importer = Importer(models=models)
        with self.assertRaises(CommandError) as context:
            importer.get_validated_models()
        self.assertEqual("'fake.modelname' is not recognised as a model name.", str(context.exception))

    def test_get_validated_models_with_single_valid_model(self):
        models = ["tests.Advert"]
        importer = Importer(models=models)
        models = importer.get_validated_models()
        self.assertListEqual(models, [Advert])

    def test_get_validated_models_with_multiple_valid_models(self):
        models = ["tests.Advert", "tests.SimplePage"]
        importer = Importer(models=models)
        models = importer.get_validated_models()
        self.assertListEqual(models, [Advert, SimplePage])

    def test_get_model_for_path(self):
        importer = Importer(models=[])
        advert_model = importer.get_model_for_path("tests.Advert")
        self.assertEqual(advert_model, Advert)
        simple_page = importer.get_model_for_path("tests.SimplePage")
        self.assertEqual(simple_page, SimplePage)
        with self.assertRaises(ObjectDoesNotExist) as context:
            bad_model_path = importer.get_model_for_path("tests.BadModelPathName")
        self.assertEqual("ContentType matching query does not exist.", str(context.exception))

    def test_get_model_serializer(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        self.assertEqual(advert_serializer, AdvertSerializer)

    def test_get_incorrect_model_serializer(self):
        importer = Importer(models=["tests.Advert"])
        with self.assertRaises(AttributeError) as context:
            advert_serializer = importer.get_model_serializer("tests.serializers.MissingSerializer")
        self.assertEqual("module 'tests.serializers' has no attribute 'MissingSerializer'", str(context.exception))

    def test__find_parent_model(self):
        importer = Importer(models=["tests.Advert"])

        # Has parent settings
        model_settings = importer._find_parent_model("tests.SimilarToAdvert")
        self.assertEqual(type(model_settings), dict)
        self.assertDictEqual(settings.AIRTABLE_IMPORT_SETTINGS['tests.Advert'], model_settings)

        # Has no parent settings
        model_settings = importer._find_parent_model("tests.MissingModelSetting")
        self.assertEqual(type(model_settings), dict)
        self.assertEqual(model_settings, {})

    def test_get_model_settings(self):
        importer = Importer()
        # Finds config settings
        advert_settings = importer.get_model_settings(Advert)
        self.assertEqual(type(advert_settings), dict)
        self.assertDictEqual(settings.AIRTABLE_IMPORT_SETTINGS['tests.Advert'], advert_settings)

        # Does not find config settings
        unused_model_settings = importer.get_model_settings(ModelNotUsed)
        self.assertEqual(type(unused_model_settings), dict)
        self.assertDictEqual(unused_model_settings, {})

        # Finds adjacent model settings
        advert_settings = importer.get_model_settings(SimilarToAdvert)
        self.assertEqual(type(advert_settings), dict)
        self.assertDictEqual(settings.AIRTABLE_IMPORT_SETTINGS['tests.Advert'], advert_settings)

    def test_get_column_to_field_names(self):
        importer = Importer()
        # The airtable column is the same name as the django field name
        # ie: slug and slug
        column, field = importer.get_column_to_field_names('slug')
        self.assertEqual(column, 'slug')
        self.assertEqual(field, 'slug')
        # The airtable column is different from the django field name
        # ie: "Page Title" and "title"
        column, field = importer.get_column_to_field_names({"Page Title": "title"})
        self.assertEqual(column, 'Page Title')
        self.assertEqual(field, 'title')
        # Different settings were specified and arent currently handled
        # Returns empty values
        column, field = importer.get_column_to_field_names(None)
        self.assertEqual(column, None)
        self.assertEqual(field, None)

    def test_get_or_set_cached_records(self):
        importer = Importer()
        self.assertEqual(importer.cached_records, {})

        # Make one API call. Update the cached_records.
        client1 = MockAirtable()
        all_records = importer.get_or_set_cached_records(client1)
        client1.get_all.assert_called()
        self.assertEqual(len(all_records), 4)

        cached_records = {
            client1.table_name: all_records
        }
        self.assertEqual(importer.cached_records, cached_records)
        self.assertEqual(len(importer.cached_records), 1)

        # Second API call is the same. Use the pre-existing cached records.
        client2 = MockAirtable()
        all_records = importer.get_or_set_cached_records(client2)
        self.assertEqual(importer.cached_records, cached_records)
        self.assertEqual(len(importer.cached_records), 1)

        # Third API call will create a new cached record in the cached_records dict
        client3 = MockAirtable()
        client3.table_name = "second_cached_entry"
        all_records = importer.get_or_set_cached_records(client3)
        self.assertNotEqual(importer.cached_records, cached_records)
        self.assertEqual(len(importer.cached_records), 2)
        # Ensure the internal dictionary "cache" has been updated
        cached_records["second_cached_entry"] = all_records
        self.assertEqual(importer.cached_records, cached_records)

    def test_convert_mapped_fields(self):
        importer = Importer()
        record_fields_dict = {
            "Page Title": "Red! It's the new blue!",
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "Is Active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
            "extra_field_from_airtable": "Not mapped",
        }
        mapped_fields_dict = {
            "Page Title": "title",
            "SEO Description": "description",
            "External Link": "external_link",
            "Is Active": "is_active",
            "slug": "slug",
        }
        mapped_fields = importer.convert_mapped_fields(
            record_fields_dict,
            mapped_fields_dict,
        )
        # Ensure the new mapped fields have the proper django field keys
        # And that each value is the value from the airtable record.
        self.assertEqual(
            mapped_fields['title'],
            "Red! It's the new blue!",
        )
        self.assertEqual(
            mapped_fields['description'],
            "Red is a scientifically proven...",
        )
        # Ensure a field from Airtable that's not mapped to a model does not get
        # passed into the newly mapped fields
        self.assertFalse(hasattr(mapped_fields, 'extra_field_from_airtable'))


class TestImportCommand(TestCase):

    def setUp(self):
        pass

    def test_import_command(self):
        from django.core.management import call_command
        message = call_command("import_airtable", "tests.Advert", verbosity=1)
