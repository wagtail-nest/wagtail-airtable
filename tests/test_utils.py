from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from django.test import TestCase

from wagtail_airtable.utils import get_model_for_path, get_all_models, get_validated_models

from tests.models import Advert, ModelNotUsed, SimilarToAdvert, SimplePage
from tests.serializers import AdvertSerializer



class TestUtilFunctions(TestCase):

    def test_get_model_for_path(self):
        advert_model = get_model_for_path("tests.Advert")
        self.assertEqual(advert_model, Advert)
        simple_page = get_model_for_path("tests.SimplePage")
        self.assertEqual(simple_page, SimplePage)
        with self.assertRaises(ObjectDoesNotExist) as context:
            bad_model_path = get_model_for_path("tests.BadModelPathName")
        self.assertEqual("ContentType matching query does not exist.", str(context.exception))

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
        with self.assertRaises(CommandError) as context:
            get_validated_models(models=models)
        self.assertEqual("'fake.ModelName' is not recognised as a model name.", str(context.exception))

    def test_get_all_models(self):
        available_models = get_all_models()
        self.assertListEqual(available_models, [SimplePage, Advert, SimilarToAdvert])