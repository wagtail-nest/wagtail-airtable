# from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from wagtail_airtable.serializers import AirtableSerializer


class AdvertSerializer(AirtableSerializer):

    slug = serializers.CharField(max_length=100, required=True)
    title = serializers.CharField(max_length=255)
