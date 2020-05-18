# AIRTABLE SETTINGS
WAGTAIL_AIRTABLE_ENABLED = True
WAGTAIL_AIRTABLE_DEBUG = True
AIRTABLE_IMPORT_SETTINGS = {
    # Applies to model_example.py
    "yourapp.YourModel": {
        "AIRTABLE_BASE_KEY": "",  # The Airtable Base Code
        "AIRTABLE_TABLE_NAME": "Your Table Name",  # Airtable Bases can have multiple tables. Tell it which one to use.
        "AIRTABLE_UNIQUE_IDENTIFIER": "slug",  # Must match the Airtable Column name
        "AIRTABLE_SERIALIZER": "yourapp.serializers.YourModelSerializer",  # A custom serializer for validating imported data.
    },
    # Applies to page_example.py
    "yourapp.HomePage": {
        "AIRTABLE_BASE_KEY": "",  # The Airtable Base Code
        "AIRTABLE_TABLE_NAME": "Your Table Name",  # Airtable Bases can have multiple tables. Tell it which one to use.
        "AIRTABLE_UNIQUE_IDENTIFIER": {  # Takes an {'Airtable Column Name': 'django_field_name'} mapping
            "Wagtail Page ID": "pk",
        },
        "AIRTABLE_SERIALIZER": "yourapp.serializers.YourPageSerializer",  # A custom serializer for validating imported data.
    },
    # Applies to multi_page_example.py
    "yourapp.HomePage2": {
        "AIRTABLE_BASE_KEY": "",
        "AIRTABLE_TABLE_NAME": "Your Table Name",
        "AIRTABLE_UNIQUE_IDENTIFIER": {"Wagtail Page ID": "pk",},
        "AIRTABLE_SERIALIZER": "yourapp.serializers.YourPageSerializer",
        # 👇 Optional setting. When `AirtableMixin` is applied to these models and these models are
        # 👇 saved, they will be treated the same as yourapp.HomePage2 (declared on of line 22)
        "EXTRA_SUPPORTED_MODELS": [
            "yourapp.ContactPage",
            "yourapp.BlogPage",
            "yourapp.MiscPage",
        ],
    },
    # {
    #     ... More settings
    # }
}
