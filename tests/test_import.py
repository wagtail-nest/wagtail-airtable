import copy
from django.conf import settings
from django.test import TestCase, override_settings
from unittest.mock import MagicMock, patch
from wagtail import hooks
from wagtail.models import Page

from tests.models import Advert, ModelNotUsed, SimilarToAdvert, SimplePage
from tests.serializers import AdvertSerializer
from wagtail_airtable.importer import AirtableModelImporter, get_column_to_field_names, convert_mapped_fields, get_data_for_new_model

from .mock_airtable import get_mock_airtable


class TestImportClass(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        airtable_patcher = patch("wagtail_airtable.importer.Airtable", new_callable=get_mock_airtable())
        self.mock_airtable = airtable_patcher.start()
        self.addCleanup(airtable_patcher.stop)

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

    def test_get_model_serializer(self):
        self.assertEqual(AirtableModelImporter(model=Advert).model_serializer, AdvertSerializer)

    def test_get_model_settings(self):
        # Finds config settings
        self.assertDictEqual(AirtableModelImporter(model=Advert).model_settings, settings.AIRTABLE_IMPORT_SETTINGS['tests.Advert'])

        # Does not find config settings
        with self.assertRaises(KeyError):
            AirtableModelImporter(model=ModelNotUsed)

        # Finds adjacent model settings
        self.assertDictEqual(AirtableModelImporter(model=SimilarToAdvert).model_settings, settings.AIRTABLE_IMPORT_SETTINGS['tests.Advert'])

    def test_get_column_to_field_names(self):
        # The airtable column is the same name as the django field name
        # ie: slug and slug
        column, field = get_column_to_field_names('slug')
        self.assertEqual(column, 'slug')
        self.assertEqual(field, 'slug')
        # The airtable column is different from the django field name
        # ie: "Page Title" and "title"
        column, field = get_column_to_field_names({"Page Title": "title"})
        self.assertEqual(column, 'Page Title')
        self.assertEqual(field, 'title')
        # Different settings were specified and arent currently handled
        # Returns empty values
        column, field = get_column_to_field_names(None)
        self.assertEqual(column, None)
        self.assertEqual(field, None)

    def test_convert_mapped_fields(self):
        record_fields_dict = self.get_valid_record_fields()
        record_fields_dict['extra_field_from_airtable'] = "Not mapped"
        mapped_fields = convert_mapped_fields(
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
        importer = AirtableModelImporter(model=Advert)
        advert = Advert.objects.get(airtable_record_id="recNewRecordId")
        self.assertNotEqual(advert.title, "Red! It's the new blue!")
        self.assertEqual(len(advert.publications.all()), 0)

        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            updated_result = next(result for result in importer.run() if not result.new)

        self.assertEqual(updated_result.record_id, advert.airtable_record_id)
        self.assertIsNone(updated_result.errors)
        hook_fn.assert_called_once_with(instance=advert, is_wagtail_page=False, record_id="recNewRecordId")

        advert.refresh_from_db()
        self.assertEqual(advert.title, "Red! It's the new blue!")
        self.assertEqual(updated_result.record_id, "recNewRecordId")
        self.assertEqual(len(advert.publications.all()), 3)

    @patch('wagtail_airtable.mixins.Airtable')
    def test_create_object(self, mixin_airtable):
        importer = AirtableModelImporter(model=Advert)
        self.assertFalse(Advert.objects.filter(slug="test-created").exists())
        self.assertFalse(Advert.objects.filter(airtable_record_id="test-created-id").exists())
        self.mock_airtable.get_all.return_value = [{
            "id": "test-created-id",
            "fields": {
                "title": "The created one",
                "description": "This one, we created.",
                "external_link": "https://example.com/",
                "is_active": True,
                "rating": "1.5",
                "long_description": "<p>Long description is long.</p>",
                "points": 95,
                "slug": "test-created",
                "publications": [
                    {"title": "Created record publication 1"},
                    {"title": "Created record publication 2"},
                    {"title": "Created record publication 3"},
                ],
            },
        }]

        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            created_result = next(importer.run())

        self.assertTrue(created_result.new)
        self.assertIsNone(created_result.errors)

        advert = Advert.objects.get(airtable_record_id=created_result.record_id)
        hook_fn.assert_called_once_with(instance=advert, is_wagtail_page=False, record_id="test-created-id")
        self.assertEqual(advert.title, "The created one")
        self.assertEqual(advert.slug, "test-created")
        self.assertEqual(len(advert.publications.all()), 3)

    def test_update_object_with_invalid_serialized_data(self):
        advert = Advert.objects.get(airtable_record_id="recNewRecordId")
        importer = AirtableModelImporter(model=Advert)
        self.assertNotEqual(advert.description, "Red is a scientifically proven..")
        self.mock_airtable.get_all()[0]['fields'] = {
            "SEO Description": "Red is a scientifically proven...",
            "External Link": "https://example.com/",
            "slug": "red-its-new-blue",
            "Rating": "2.5",
        }
        result = next(importer.run())
        self.assertEqual(result.errors, {'title': ['This field is required.']})
        advert.refresh_from_db()
        self.assertNotEqual(advert.description, "Red is a scientifically proven..")

    def test_get_existing_instance(self):
        importer = AirtableModelImporter(model=Advert)
        advert = Advert.objects.get(airtable_record_id="recNewRecordId")

        self.assertEqual(importer.get_existing_instance("recNewRecordId", None), advert)

        self.assertEqual(importer.airtable_unique_identifier_field_name, "slug")
        self.assertEqual(importer.get_existing_instance("nothing", advert.slug), advert)

    def test_is_wagtail_page(self):
        self.assertTrue(AirtableModelImporter(SimplePage).model_is_page)
        self.assertFalse(AirtableModelImporter(Advert).model_is_page)

    def test_get_data_for_new_model(self):
        mapped_fields = convert_mapped_fields(
            self.get_valid_record_fields(),
            self.get_valid_mapped_fields(),
        )

        data_for_new_model = get_data_for_new_model(mapped_fields, 'recSomeRecordId')
        self.assertTrue(data_for_new_model.get('airtable_record_id'))
        self.assertEqual(data_for_new_model['airtable_record_id'], 'recSomeRecordId')
        self.assertIsNone(data_for_new_model.get('id'))
        self.assertIsNone(data_for_new_model.get('pk'))

    @patch('wagtail_airtable.mixins.Airtable')
    def test_create_page(self, mixin_airtable):
        importer = AirtableModelImporter(model=SimplePage)
        self.assertEqual(Page.objects.get(slug="home").get_children().count(), 0)

        self.mock_airtable.get_all.return_value = [{
            "id": "test-created-page-id",
            "fields": {
                "title": "A simple page",
                "slug": "a-simple-page",
                "intro": "How much more simple can it get? And the answer is none. None more simple.",
            },
        }]
        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            created_result = next(importer.run())
        self.assertTrue(created_result.new)
        self.assertIsNone(created_result.errors)

        page = Page.objects.get(slug="home").get_children().first().specific
        self.assertIsInstance(page, SimplePage)
        hook_fn.assert_called_once_with(instance=page, is_wagtail_page=True, record_id="test-created-page-id")
        self.assertEqual(page.title, "A simple page")
        self.assertEqual(page.slug, "a-simple-page")
        self.assertEqual(page.intro, "How much more simple can it get? And the answer is none. None more simple.")
        self.assertFalse(page.live)

    @patch('wagtail_airtable.mixins.Airtable')
    def test_create_and_publish_page(self, mixin_airtable):
        new_settings = copy.deepcopy(settings.AIRTABLE_IMPORT_SETTINGS)
        new_settings['tests.SimplePage']['AUTO_PUBLISH_NEW_PAGES'] = True
        with override_settings(AIRTABLE_IMPORT_SETTINGS=new_settings):
            importer = AirtableModelImporter(model=SimplePage)
            self.assertEqual(Page.objects.get(slug="home").get_children().count(), 0)

            self.mock_airtable.get_all.return_value = [{
                "id": "test-created-page-id",
                "fields": {
                    "title": "A simple page",
                    "slug": "a-simple-page",
                    "intro": "How much more simple can it get? And the answer is none. None more simple.",
                },
            }]
            hook_fn = MagicMock()
            with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
                created_result = next(importer.run())
            self.assertTrue(created_result.new)
            self.assertIsNone(created_result.errors)

            page = Page.objects.get(slug="home").get_children().first().specific
            self.assertIsInstance(page, SimplePage)
            hook_fn.assert_called_once_with(instance=page, is_wagtail_page=True, record_id="test-created-page-id")
            self.assertEqual(page.title, "A simple page")
            self.assertEqual(page.slug, "a-simple-page")
            self.assertEqual(page.intro, "How much more simple can it get? And the answer is none. None more simple.")
            self.assertTrue(page.live)

    @patch('wagtail_airtable.mixins.Airtable')
    def test_update_page(self, mixin_airtable):
        importer = AirtableModelImporter(model=SimplePage)
        parent_page = Page.objects.get(slug="home")
        page = SimplePage(
            title="A simple page",
            slug="a-simple-page",
            intro="How much more simple can it get? And the answer is none. None more simple.",
        )
        page.push_to_airtable = False
        parent_page.add_child(instance=page)
        self.assertEqual(page.revisions.count(), 0)

        self.mock_airtable.get_all.return_value = [{
            "id": "test-created-page-id",
            "fields": {
                "title": "A simple page",
                "slug": "a-simple-page",
                "intro": "How much more simple can it get? Oh, actually it can get more simple.",
            },
        }]
        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            updated_result = next(importer.run())
        self.assertFalse(updated_result.new)
        self.assertIsNone(updated_result.errors)

        page.refresh_from_db()
        hook_fn.assert_called_once_with(instance=page, is_wagtail_page=True, record_id="test-created-page-id")
        self.assertEqual(page.title, "A simple page")
        self.assertEqual(page.slug, "a-simple-page")
        self.assertEqual(page.intro, "How much more simple can it get? Oh, actually it can get more simple.")
        self.assertEqual(page.revisions.count(), 1)

    @patch('wagtail_airtable.mixins.Airtable')
    def test_skip_update_page_if_unchanged(self, mixin_airtable):
        importer = AirtableModelImporter(model=SimplePage)
        parent_page = Page.objects.get(slug="home")
        page = SimplePage(
            title="A simple page",
            slug="a-simple-page",
            intro="How much more simple can it get? And the answer is none. None more simple.",
        )
        page.push_to_airtable = False
        parent_page.add_child(instance=page)
        self.assertEqual(page.revisions.count(), 0)

        self.mock_airtable.get_all.return_value = [{
            "id": "test-created-page-id",
            "fields": {
                "title": "A simple page",
                "slug": "a-simple-page",
                "intro": "How much more simple can it get? And the answer is none. None more simple.",
            },
        }]
        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            updated_result = next(importer.run())
        self.assertFalse(updated_result.new)
        self.assertIsNone(updated_result.errors)
        hook_fn.assert_not_called()

        self.assertEqual(page.revisions.count(), 0)

    @patch('wagtail_airtable.mixins.Airtable')
    def test_skip_update_page_if_locked(self, mixin_airtable):
        importer = AirtableModelImporter(model=SimplePage)
        parent_page = Page.objects.get(slug="home")
        page = SimplePage(
            title="A simple page",
            slug="a-simple-page",
            intro="How much more simple can it get? And the answer is none. None more simple.",
        )
        page.push_to_airtable = False
        page.locked = True
        parent_page.add_child(instance=page)
        self.assertEqual(page.revisions.count(), 0)

        self.mock_airtable.get_all.return_value = [{
            "id": "test-created-page-id",
            "fields": {
                "title": "A simple page",
                "slug": "a-simple-page",
                "intro": "How much more simple can it get? Oh, actually it can get more simple.",
            },
        }]
        hook_fn = MagicMock()
        with hooks.register_temporarily("airtable_import_record_updated", hook_fn):
            updated_result = next(importer.run())
        self.assertFalse(updated_result.new)
        self.assertIsNone(updated_result.errors)
        hook_fn.assert_not_called()

        self.assertEqual(page.revisions.count(), 0)
        page.refresh_from_db()
        self.assertEqual(page.intro, "How much more simple can it get? And the answer is none. None more simple.")
