from django.conf import settings
from django.test import TestCase, TransactionTestCase

from tests.models import Advert, ModelNotUsed, SimilarToAdvert, SimplePage
from tests.serializers import AdvertSerializer
from wagtail_airtable.management.commands.import_airtable import Importer
from wagtail_airtable.tests import MockAirtable


class TestImportClass(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.options = {
            'verbosity': 2
        }

    def get_valid_record_fields(self):
        """Common used method for standard valid airtable records."""
        return {
            "Page Title": "Red! It's the new blue!",
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "Is Active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
        }

    def get_valid_mapped_fields(self):
        """Common used method for standard valid airtable mapped fields."""
        return {
            "Page Title": "title",
            "SEO Description": "description",
            "External Link": "external_link",
            "Is Active": "is_active",
            "slug": "slug",
        }

    def get_invalid_record_fields(self):
        """Common used method for standard invalid airtable records."""
        return {
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "slug": "red-its-new-blue",
        }

    def get_invalid_mapped_fields(self):
        """Common used method for standard invalid airtable mapped fields."""
        return {
            "SEO Description": "description",
            "External Link": "external_link",
            "slug": "slug",
        }

    def test_debug_message(self):
        models = ["fake.ModelName"]
        text = "Testing debug message with high verbosity"

        importer = Importer(models=models, options=self.options)
        debug_message = importer.debug_message(text)
        self.assertEqual(debug_message, text)

        # Lower verbosity
        importer = Importer(models=models, options={'verbosity': 1})
        debug_message = importer.debug_message(text)
        self.assertEqual(debug_message, None)

    def test_get_model_serializer(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        self.assertEqual(advert_serializer, AdvertSerializer)

    def test_get_incorrect_model_serializer(self):
        importer = Importer(models=["tests.Advert"])
        with self.assertRaises(AttributeError) as context:
            importer.get_model_serializer("tests.serializers.MissingSerializer")
        self.assertEqual("module 'tests.serializers' has no attribute 'MissingSerializer'", str(context.exception))

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

    def test_check_field_is_m2m(self):
        importer = Importer()

        client = MockAirtable()
        records = client.get_all()
        client.get_all.assert_called()
        for i, record in enumerate(records):
            for field_name, value, m2m in importer.get_fields_and_m2m_status(Advert, record["fields"]):
                if field_name == "publications":
                    self.assertEqual(m2m, True)
                else:
                    self.assertEqual(m2m, False)

    def test_update_m2m_fields(self):
        importer = Importer()

        client = MockAirtable()
        records = client.get_all()
        client.get_all.assert_called()
        advert = Advert.objects.first()
        self.assertEqual(len(advert.publications.all()), 0)

        advert_serializer = AdvertSerializer(data=records[0]["fields"])
        self.assertEqual(advert_serializer.is_valid(), True)

        publications_dict = advert_serializer.validated_data["publications"]

        importer.update_model_m2m_fields(advert, "publications", publications_dict)

        self.assertEqual(len(advert.publications.all()), 3)

    def test_convert_mapped_fields(self):
        importer = Importer()
        record_fields_dict = self.get_valid_record_fields()
        record_fields_dict['extra_field_from_airtable'] = "Not mapped"
        mapped_fields = importer.convert_mapped_fields(
            record_fields_dict,
            self.get_valid_mapped_fields(),
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

    def test_update_object(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        record_fields_dict = self.get_valid_record_fields()
        record_fields_dict["SEO Description"] = "Red is a scientifically proven..."
        mapped_fields = importer.convert_mapped_fields(
            record_fields_dict,
            self.get_valid_mapped_fields(),
        )
        # Ensure mapped_fields are mapped properly
        self.assertEqual(
            mapped_fields['description'],
            "Red is a scientifically proven...",
        )
        # Check serialized data is valid
        serialized_data = advert_serializer(data=mapped_fields)
        is_valid = serialized_data.is_valid()
        self.assertTrue(is_valid)
        # Get the advert object.
        instance = Advert.objects.first()
        self.assertEqual(instance.airtable_record_id, '')
        # Importer should have zero updates objects.
        self.assertEqual(importer.updated, 0)

        saved = importer.update_object(instance, 'recNewRecordId', serialized_data)

        self.assertTrue(saved)
        # Check to make sure _skip_signals is set.
        self.assertTrue(instance._skip_signals)
        self.assertEqual(importer.updated, 1)
        self.assertEqual(importer.records_used, ['recNewRecordId'])
        # Re-fetch the Advert instance and check its airtable_record_id
        instance = Advert.objects.first()
        self.assertEqual(instance.airtable_record_id, 'recNewRecordId')

    def test_update_object_with_invalid_serialized_data(self):
        instance = Advert.objects.first()
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        record_fields_dict = {
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "slug": "red-its-new-blue",
            "Rating": "2.5",
        }
        mapped_fields_dict = {
            "SEO Description": "description",
            "External Link": "external_link",
            "slug": "slug",
            "Rating": "rating",
        }
        mapped_fields = importer.convert_mapped_fields(
            record_fields_dict,
            mapped_fields_dict,
        )
        serialized_data = advert_serializer(data=mapped_fields)
        is_valid = serialized_data.is_valid()
        self.assertFalse(is_valid)
        saved = importer.update_object(instance, 'recNewRecordId', serialized_data)
        self.assertTrue(saved)

    def test_update_object_by_uniq_col_name_missing_uniq_id(self):
        importer = Importer()
        updated = importer.update_object_by_uniq_col_name(
            field_mapping={'slug': ''},
            model=Advert,
            serialized_data=object,
            record_id='',
        )

        self.assertFalse(updated)
        self.assertEqual(importer.skipped, 1)

    def test_update_object_by_uniq_col_name_object_found(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        record_fields_dict = {
            "Page Title": "Red! It's the new blue!",
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/UPDATED",
            "Is Active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
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
        # Check serialized data is valid
        serialized_data = advert_serializer(data=mapped_fields)
        self.assertTrue(serialized_data.is_valid())

        # with self.assertRaises(AttributeError)
        updated = importer.update_object_by_uniq_col_name(
            field_mapping={'slug': 'red-its-new-blue'},
            model=Advert,
            serialized_data=serialized_data,
            record_id='recNewRecordId',
        )
        self.assertTrue(updated)
        self.assertEqual(importer.skipped, 0)
        self.assertEqual(importer.updated, 1)

        advert = Advert.objects.get(slug="red-its-new-blue")
        self.assertEqual(advert.external_link, "https://example.com/UPDATED")

    def test_update_object_by_uniq_col_name_object_not_found(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        record_fields_dict = {
            "Page Title": "Red! It's the new blue!",
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "Is Active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
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
        # Check serialized data is valid
        serialized_data = advert_serializer(data=mapped_fields)
        self.assertTrue(serialized_data.is_valid())

        # with self.assertRaises(AttributeError)
        updated = importer.update_object_by_uniq_col_name(
            field_mapping={'slug': 'MISSING-OBJECT'},
            model=Advert,
            serialized_data=serialized_data,
            record_id='recNewRecordId',
        )
        self.assertFalse(updated)
        self.assertEqual(importer.updated, 0)

    def test_is_wagtail_page(self):
        importer = Importer()
        self.assertTrue(importer.is_wagtail_page(SimplePage))
        self.assertFalse(importer.is_wagtail_page(Advert))

    def test_get_data_for_new_model_with_valid_serialized_data(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")
        mapped_fields = importer.convert_mapped_fields(
            self.get_valid_record_fields(),
            self.get_valid_mapped_fields(),
        )
        # Check serialized data is valid
        serialized_data = advert_serializer(data=mapped_fields)
        is_valid = serialized_data.is_valid()
        self.assertTrue(is_valid)

        data_for_new_model = importer.get_data_for_new_model(serialized_data, mapped_fields, 'recSomeRecordId')
        self.assertTrue(data_for_new_model.get('airtable_record_id'))
        self.assertEqual(data_for_new_model['airtable_record_id'], 'recSomeRecordId')
        self.assertIsNone(data_for_new_model.get('id'))
        self.assertIsNone(data_for_new_model.get('pk'))

        new_dict = dict(serialized_data.validated_data)
        new_dict['airtable_record_id'] = 'recSomeRecordId'
        self.assertDictEqual(new_dict, data_for_new_model)

    def test_get_data_for_new_model_with_invalid_serialized_data(self):
        importer = Importer(models=["tests.Advert"])
        advert_serializer = importer.get_model_serializer("tests.serializers.AdvertSerializer")

        mapped_fields = importer.convert_mapped_fields(
            self.get_invalid_record_fields(),
            self.get_invalid_mapped_fields(),
        )
        # Check serialized data is valid
        serialized_data = advert_serializer(data=mapped_fields)
        is_valid = serialized_data.is_valid()
        self.assertFalse(is_valid)

        data_for_new_model = importer.get_data_for_new_model(serialized_data, mapped_fields, 'recSomeRecordId')
        self.assertTrue(data_for_new_model.get('airtable_record_id'))
        self.assertEqual(data_for_new_model['airtable_record_id'], 'recSomeRecordId')
        self.assertIsNone(data_for_new_model.get('id'))
        self.assertIsNone(data_for_new_model.get('pk'))

        new_dict = mapped_fields.copy()
        new_dict['airtable_record_id'] = 'recSomeRecordId'
        self.assertDictEqual(data_for_new_model, {'airtable_record_id': 'recSomeRecordId'})


class TestImportCommand(TransactionTestCase):

    def test_import_command(self):
        from django.core.management import call_command
        call_command("import_airtable", "tests.Advert", verbosity=1)
