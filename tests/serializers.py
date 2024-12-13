# from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from wagtail_airtable.serializers import AirtableSerializer


class PublicationsObjectsSerializer(serializers.RelatedField):
    """
    Let's assume there's a "bank_name" column in Airtable but it stores a string.

    When importing from Airtable you'll need to find a model object based on that name.
    That's what this serializer is doing.

    Usage:
    class YourModelSerializer(AirtableSerializer):
        ...
        bank_name = BankNameSerializer(required=False)
        ...
    """

    def to_internal_value(self, data):
        from .models import Publication
        publications = []
        if data:
            for publication in data:
                publication_obj, _ = Publication.objects.get_or_create(title=publication["title"])
                publications.append(publication_obj)
            return publications
        return data

    def get_queryset(self):
        pass


class AdvertSerializer(AirtableSerializer):
    slug = serializers.CharField(max_length=100, required=True)
    title = serializers.CharField(max_length=255)
    external_link = serializers.URLField(required=False)
    publications = PublicationsObjectsSerializer(required=False)


class SimplePageSerializer(AirtableSerializer):
    title = serializers.CharField(max_length=255, required=True)
    slug = serializers.CharField(max_length=100, required=True)
    intro = serializers.CharField()
