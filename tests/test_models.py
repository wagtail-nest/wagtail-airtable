from copy import copy

from django.test import TestCase
from pyairtable.formulas import match

from tests.models import Advert, SimplePage
from wagtail_airtable.mixins import AirtableMixin
from unittest.mock import ANY, patch
from .mock_airtable import get_mock_airtable


class TestAirtableModel(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        airtable_patcher = patch("wagtail_airtable.mixins.Api", new_callable=get_mock_airtable())
        airtable_patcher.start()
        self.addCleanup(airtable_patcher.stop)

        self.client.login(username='admin', password='password')
        self.advert = Advert.objects.first()

    def test_model_connection_settings(self):
        # Make sure the settings are being passed into the model after .setup_airtable() is called
        advert = copy(self.advert)
        advert.setup_airtable()
        self.assertEqual(advert.AIRTABLE_BASE_KEY, 'app_airtable_advert_base_key')
        self.assertEqual(advert.AIRTABLE_TABLE_NAME, 'Advert Table Name')
        self.assertEqual(advert.AIRTABLE_UNIQUE_IDENTIFIER, 'slug')
        self.assertEqual(advert.AIRTABLE_SERIALIZER, 'tests.serializers.AdvertSerializer')

    def test_model_connection_settings_before_setup(self):
        # Make sure instances are not instantiated with Airtable settings.
        # By preventing automatic Airtable API instantiation we can avoid
        # holding an Airtable API object on every model instance in Wagtail List views.
        advert = copy(self.advert)
        self.assertEqual(advert.AIRTABLE_BASE_KEY, None)
        self.assertEqual(advert.AIRTABLE_TABLE_NAME, None)
        self.assertEqual(advert.AIRTABLE_UNIQUE_IDENTIFIER, None)
        # Object don't need to store the AIRTABLE_SERIALIZER property on them.
        # Thus they should not have the property at all.
        self.assertFalse(hasattr(advert, 'AIRTABLE_SERIALIZER'))

    def test_get_export_fields(self):
        self.assertTrue(hasattr(self.advert, 'get_export_fields'))
        export_fields = self.advert.get_export_fields()
        self.assertEqual(type(export_fields), dict)

    def test_get_import_fields(self):
        self.assertTrue(hasattr(self.advert, 'map_import_fields'))
        mapped_import_fields = self.advert.map_import_fields()
        self.assertEqual(type(mapped_import_fields), dict)

    def test_create_object_from_url(self):
        self.client.post('/admin/snippets/tests/advert/add/', {
            'title': 'Second advert',
            'description': 'Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            'rating': "1.5",
            'slug': 'second-advert',
        })
        advert = Advert.objects.last()
        self.assertEqual(advert.airtable_record_id, 'recNewRecordId')
        self.assertEqual(advert.title, 'Second advert')
        self.assertFalse(advert._ran_airtable_setup)
        self.assertFalse(advert._is_enabled)
        self.assertFalse(advert._push_to_airtable)
        self.assertFalse(hasattr(advert, 'airtable_client'))

        advert.setup_airtable()

        self.assertEqual(advert.AIRTABLE_BASE_KEY, 'app_airtable_advert_base_key')
        self.assertEqual(advert.AIRTABLE_TABLE_NAME, 'Advert Table Name')
        self.assertEqual(advert.AIRTABLE_UNIQUE_IDENTIFIER, 'slug')
        self.assertTrue(advert._ran_airtable_setup)
        self.assertTrue(advert._is_enabled)
        self.assertTrue(advert._push_to_airtable)
        self.assertTrue(hasattr(advert, 'airtable_client'))

    def test_create_object_with_existing_airtable_record_id(self):
        advert = Advert.objects.create(
            title='Testing creation',
            description='Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            rating="2.5",
            slug='testing-creation',
            airtable_record_id='recNewRecordId',
        )
        # save_to_airtable will confirm that a record with the given ID exists
        # and update that record
        advert.airtable_client._table.get.assert_called_once_with('recNewRecordId')
        advert.airtable_client._table.update.assert_called_once_with('recNewRecordId', ANY)
        call_args = advert.airtable_client._table.update.call_args.args
        self.assertEqual(call_args[1]['title'], 'Testing creation')
        advert.airtable_client._table.create.assert_not_called()

    def test_create_object_with_missing_id_and_matching_airtable_record(self):
        advert = Advert.objects.create(
            title='Testing creation',
            description='Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            rating="2.5",
            slug='a-matching-slug',
            airtable_record_id='recMissingRecordId',
        )
        # save_to_airtable will find that a record with the given ID does not exist,
        # but one matching the slug does, and update that record
        advert.airtable_client._table.get.assert_called_once_with('recMissingRecordId')
        advert.airtable_client._table.all.assert_called_once_with(formula=match({'slug': 'a-matching-slug'}))
        advert.airtable_client._table.update.assert_called_once_with('recMatchedRecordId', ANY)
        call_args = advert.airtable_client._table.update.call_args.args
        self.assertEqual(call_args[1]['title'], 'Testing creation')
        advert.airtable_client._table.create.assert_not_called()
        advert.refresh_from_db()
        self.assertEqual(advert.airtable_record_id, 'recMatchedRecordId')

    def test_create_object_with_no_id_and_matching_airtable_record(self):
        advert = Advert.objects.create(
            title='Testing creation',
            description='Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            rating="2.5",
            slug='a-matching-slug',
        )
        # save_to_airtable will skip the lookup by ID, but find a record matching the slug,
        # and update that record
        advert.airtable_client._table.get.assert_not_called()
        advert.airtable_client._table.all.assert_called_once_with(formula=match({'slug': 'a-matching-slug'}))
        advert.airtable_client._table.update.assert_called_once_with('recMatchedRecordId', ANY)
        call_args = advert.airtable_client._table.update.call_args.args
        self.assertEqual(call_args[1]['title'], 'Testing creation')
        advert.airtable_client._table.create.assert_not_called()
        advert.refresh_from_db()
        self.assertEqual(advert.airtable_record_id, 'recMatchedRecordId')

    def test_create_object_with_missing_id_and_non_matching_airtable_record(self):
        advert = Advert.objects.create(
            title='Testing creation',
            description='Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            rating="2.5",
            slug='a-non-matching-slug',
            airtable_record_id='recMissingRecordId',
        )
        # save_to_airtable will find that a record with the given ID does not exist,
        # and neither does one matching the slug - so it will create a new one
        # and update the model with the new record ID
        advert.airtable_client._table.get.assert_called_once_with('recMissingRecordId')
        advert.airtable_client._table.all.assert_called_once_with(formula=match({'slug': 'a-non-matching-slug'}))
        advert.airtable_client._table.create.assert_called_once()
        call_args = advert.airtable_client._table.create.call_args.args
        self.assertEqual(call_args[0]['title'], 'Testing creation')
        advert.airtable_client._table.update.assert_not_called()
        advert.refresh_from_db()
        self.assertEqual(advert.airtable_record_id, 'recNewRecordId')

    def test_edit_object(self):
        advert = Advert.objects.get(airtable_record_id='recNewRecordId')
        advert.title = "Edited title"
        advert.description = "Edited description"
        advert.save()
        # save_to_airtable will confirm that a record with the given ID exists and update it
        advert.airtable_client._table.get.assert_called_once_with('recNewRecordId')
        advert.airtable_client._table.update.assert_called_once_with('recNewRecordId', ANY)
        call_args = advert.airtable_client._table.update.call_args.args
        advert.airtable_client._table.create.assert_not_called()
        self.assertEqual(call_args[1]['title'], 'Edited title')
        self.assertEqual(advert.title, "Edited title")

    def test_delete_object(self):
        advert = Advert.objects.get(slug='delete-me')
        self.assertEqual(advert.airtable_record_id, 'recNewRecordId')
        advert.delete()
        advert.airtable_client._table.delete.assert_called_once_with('recNewRecordId')
        find_deleted_advert = Advert.objects.filter(slug='delete-me').count()
        self.assertEqual(find_deleted_advert, 0)


class TestAirtableMixin(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        airtable_patcher = patch("wagtail_airtable.mixins.Api", new_callable=get_mock_airtable())
        self.mock_airtable = airtable_patcher.start()
        self.addCleanup(airtable_patcher.stop)

    def test_setup_airtable(self):
        advert = copy(Advert.objects.first())
        self.assertFalse(advert._ran_airtable_setup)
        self.assertFalse(advert._is_enabled)
        self.assertFalse(advert._push_to_airtable)
        self.assertFalse(hasattr(advert, 'airtable_client'))

        advert.setup_airtable()

        self.assertEqual(advert.AIRTABLE_BASE_KEY, 'app_airtable_advert_base_key')
        self.assertEqual(advert.AIRTABLE_TABLE_NAME, 'Advert Table Name')
        self.assertEqual(advert.AIRTABLE_UNIQUE_IDENTIFIER, 'slug')
        self.assertTrue(advert._ran_airtable_setup)
        self.assertTrue(advert._is_enabled)
        self.assertTrue(advert._push_to_airtable)
        self.assertTrue(hasattr(advert, 'airtable_client'))

    def test_delete_record(self):
        advert = Advert.objects.get(airtable_record_id='recNewRecordId')
        advert.setup_airtable()
        deleted = advert.delete_record()
        self.assertTrue(deleted)
        advert.airtable_client._table.delete.assert_called_once_with("recNewRecordId")

    def test_parse_request_error(self):
        error_401 = "401 Client Error: Unauthorized for url: https://api.airtable.com/v0/appYourAppId/Your%20Table?filterByFormula=.... [Error: {'type': 'AUTHENTICATION_REQUIRED', 'message': 'Authentication required'}]"
        parsed_error = AirtableMixin.parse_request_error(error_401)
        self.assertEqual(parsed_error['status_code'], 401)
        self.assertEqual(parsed_error['type'], 'AUTHENTICATION_REQUIRED')
        self.assertEqual(parsed_error['message'], 'Authentication required')

        error_404 = "404 Client Error: Not Found for url: https://api.airtable.com/v0/app3dozZtsCotiIpf/Brokerages/nope [Error: NOT_FOUND]"
        parsed_error = AirtableMixin.parse_request_error(error_404)
        self.assertEqual(parsed_error['status_code'], 404)
        self.assertEqual(parsed_error['type'], 'NOT_FOUND')
        self.assertEqual(parsed_error['message'], 'Record not found')

        error_404 = "404 Client Error: Not Found for url: https://api.airtable.com/v0/app3dozZtsCotiIpf/Brokerages%2022 [Error: {'type': 'TABLE_NOT_FOUND', 'message': 'Could not find table table_name in appxxxxx'}]"
        parsed_error = AirtableMixin.parse_request_error(error_404)
        self.assertEqual(parsed_error['status_code'], 404)
        self.assertEqual(parsed_error['type'], 'TABLE_NOT_FOUND')
        self.assertEqual(parsed_error['message'], 'Could not find table table_name in appxxxxx')

    def test_match_record(self):
        advert = Advert.objects.get(slug='red-its-new-blue')
        advert.setup_airtable()
        record_id = advert.match_record()
        self.assertEqual(record_id, 'recNewRecordId')
        advert.airtable_client._table.all.assert_called_once_with(formula=match({'slug': 'red-its-new-blue'}))

    def test_match_record_with_dict_identifier(self):
        page = SimplePage.objects.get(slug='home')
        page.setup_airtable()
        record_id = page.match_record()
        self.assertEqual(record_id, 'recHomePageId')
        page.airtable_client._table.all.assert_called_once_with(formula=match({'Page Slug': 'home'}))

    def test_check_record_exists(self):
        advert = Advert.objects.get(airtable_record_id='recNewRecordId')
        advert.setup_airtable()
        record_exists = advert.check_record_exists('recNewRecordId')
        self.assertTrue(record_exists)
        advert.airtable_client._table.get.assert_called_once_with('recNewRecordId')
