from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import TestCase

from wagtail_airtable.utils import airtable_message, can_send_airtable_messages, get_model_for_path, get_all_models, get_validated_models

from tests.models import Advert, ModelNotUsed, SimilarToAdvert, SimplePage
from tests.serializers import AdvertSerializer


class TestUtilFunctions(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test_get_model_for_path(self):
        advert_model = get_model_for_path("tests.Advert")
        self.assertEqual(advert_model, Advert)
        simple_page = get_model_for_path("tests.SimplePage")
        self.assertEqual(simple_page, SimplePage)
        bad_model_path = get_model_for_path("tests.BadModelPathName")
        self.assertFalse(bad_model_path)

    def test_get_validated_models_with_single_valid_model(self):
        models = ["tests.Advert"]
        models = get_validated_models(models=models)
        self.assertListEqual(models, [Advert])

    def test_get_validated_models_with_multiple_valid_models(self):
        models = ["tests.Advert", "tests.SimplePage", "tests.SimilarToAdvert"]
        models = get_validated_models(models=models)
        self.assertListEqual(models, [Advert, SimplePage, SimilarToAdvert])

    def test_get_validated_models_with_invalid_model(self):
        models = ["fake.ModelName"]
        with self.assertRaises(ImproperlyConfigured) as context:
            get_validated_models(models=models)
        self.assertEqual("'fake.ModelName' is not recognised as a model name.", str(context.exception))

    def test_get_all_models(self):
        available_models = get_all_models()
        self.assertListEqual(available_models, [SimplePage, Advert, SimilarToAdvert])

    def test_get_all_models_as_path(self):
        available_models = get_all_models(as_path=True)
        self.assertListEqual(available_models, ['tests.simplepage', 'tests.advert', 'tests.similartoadvert'])

    def test_can_send_airtable_messages(self):
        instance = Advert.objects.first()
        enabled = can_send_airtable_messages(instance)
        self.assertTrue(enabled)

    def test_cannot_send_airtable_messages(self):
        instance = SimplePage.objects.first()
        enabled = can_send_airtable_messages(instance)
        self.assertFalse(enabled)

    def test_airtable_messages(self):
        instance = Advert.objects.first()
        response = self.client.get('/admin/login/')
        request = response.wsgi_request
        result = airtable_message(request, instance, message="Custom message here", button_text="Custom button text")
        self.assertEqual(result, None)

        instance.airtable_record_id = 'recTestingRecordId'  # Enables the Airtable button
        result = airtable_message(request, instance, message="Second custom message here", button_text="2nd custom button text")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)

        message1 = messages[0].message
        self.assertIn('Custom message here', message1)
        self.assertNotIn('Custom button text', message1)

        message2 = messages[1].message
        self.assertIn('Second custom message here', message2)
        self.assertIn('2nd custom button text', message2)
