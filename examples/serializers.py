import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from taggit.models import Tag

from wagtail_airtable.serializers import AirtableSerializer


class TagSerializer(serializers.RelatedField):
    """
    A tag serializer to convert a string of tags (ie. `Tag1, Tag2`) into a list of Tag objects (ie. `[Tag], [Tag]`).

    If a tag in Airtable doesn't exist in Wagtail, this snippet will create a new Tag.

    Usage:
    class YourModelSerializer(AirtableSerializer):
        ...
        tags = TagSerializer(required=False)
        ...
    """

    def to_internal_value(self, data):
        if type(data) == str:
            tags = []
            for tag in data.split(","):
                tag, _ = Tag.objects.get_or_create(name=tag.strip())
                tags.append(tag)
            return tags
        elif type(data) == list:
            for tag in data:
                tag, _ = Tag.objects.get_or_create(name=tag.strip())
                tags.append(tag)
            return tags
        return data

    def get_queryset(self):
        pass


class BankNameSerializer(serializers.RelatedField):
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
        from .models import BankOrganisation

        if data:
            try:
                bank = BankOrganisation.objects.get(name=data)
            except BankOrganisation.DoesNotExist:
                return None
            else:
                return bank
        return data

    def get_queryset(self):
        pass


class DateTimeSerializer(serializers.DateTimeField):
    # Useful for parsing an Airtable Date field into a Django DateTimeField
    def to_internal_value(self, date):
        if type(date) == str and len(date):
            date = parse_datetime(date).isoformat()
        return date


class DateSerializer(serializers.DateTimeField):
    # Useful for parsing an Airtable Date field into a Django DateField
    def to_internal_value(self, date):
        if type(date) == str and len(date):
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return date


class YourModelSerializer(AirtableSerializer):
    """
    YourModel serializer used when importing Airtable records.

    This serializer will help validate data coming in from Airtable and help prevent
    malicious intentions.

    This model assumes there is a "name" mapping in YourModel.map_import_fields()
    """

    name = serializers.CharField(max_length=200, required=True)
    slug = serializers.CharField(max_length=200, required=True)


class YourPageSerializer(AirtableSerializer):
    """
    YourModel serializer used when importing Airtable records.

    This serializer will help validate data coming in from Airtable and help prevent
    malicious intentions.

    This model assumes there is a "name" mapping in YourModel.map_import_fields()
    """

    # Page.title from wagtailcore.page. Airtable can update this value.
    title = serializers.CharField(max_length=200, required=True)
    # Allow Airtable to overwrite the last_published_at date using a custom serializer.
    # This is probably a bad idea to allow this field to be imported, but it's a good code example.
    last_published_at = DateSerializer(required=False)
    # Custom field we created on `class YourPage`.
    # We want Airtable to import and validate this data before updating the value.
    name = serializers.CharField(max_length=200, required=True)
    # Not supported because we don't want a slug to be overwritten.
    # slug = serializers.CharField(max_length=200, required=True)
