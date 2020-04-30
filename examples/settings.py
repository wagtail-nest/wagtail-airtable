# AIRTABLE SETTINGS
WAGTAIL_AIRTABLE_ENABLED = True
WAGTAIL_AIRTABLE_DEBUG = True
AIRTABLE_IMPORT_SETTINGS = {
    'yourapp.YourModel': {
        'AIRTABLE_BASE_KEY': '', # The Airtable Base Code
        'AIRTABLE_TABLE_NAME': 'Your Table Name', # Airtable Bases can have multiple tables. Tell it which one to use.
        'AIRTABLE_UNIQUE_IDENTIFIER': 'slug', # Must match the Airtable Column name
        'AIRTABLE_SERIALIZER': 'yourapp.serializers.YourModelSerializer'  # A custom serializer for validating imported data.
    },
    'yourapp.HomePage': {
        'AIRTABLE_BASE_KEY': '', # The Airtable Base Code
        'AIRTABLE_TABLE_NAME': 'Your Table Name', # Airtable Bases can have multiple tables. Tell it which one to use.
        'AIRTABLE_UNIQUE_IDENTIFIER': { # Takes an {'Airtable Column Name': 'django_field_name'} mapping
            'Wagtail Page ID': 'pk',
        },
        'AIRTABLE_SERIALIZER': 'yourapp.serializers.YourPageSerializer'  # A custom serializer for validating imported data.
    },
    # {
    #     ... More settings
    # }
}
