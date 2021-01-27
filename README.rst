Wagtail/Airtable
================

An extension for Wagtail allowing content to be transferred between Airtable sheets and your Wagtail/Django models.

Developed by `Torchbox <https://torchbox.com/>`_ and sponsored by `The Motley Fool <https://www.fool.com/>`_.

.. image:: https://raw.githubusercontent.com/wagtail/wagtail-airtable/master/examples/preview.gif

`View the repo README for more details <https://github.com/wagtail/wagtail-airtable/>`_

****************************
Installation & Configuration
****************************

* Install the package with ``pip install wagtail-airtable``
* Add ``'wagtail_airtable'`` to your project's ``INSTALLED_APPS``
* In your settings you will need to map models to Airtable settings. Every model you want to map to an Airtable sheet will need:
    * An ``AIRTABLE_BASE_KEY``. You can find the base key in your Airtable docs when you're signed in to Airtable.com
    * An ``AIRTABLE_TABLE_NAME`` to determine which table to connect to.
    * An ``AIRTABLE_UNIQUE_IDENTIFIER``. This can either be a string or a dictionary mapping the Airtable column name to your unique field in your model.
        * ie. ``AIRTABLE_UNIQUE_IDENTIFIER: 'slug',`` this will match the ``slug`` field on your model with the ``slug`` column name in Airtable. Use this option if your model field and your Airtable column name are identical.
        * ie. ``AIRTABLE_UNIQUE_IDENTIFIER: {'Airtable Column Name': 'model_field_name'},`` this will map the ``Airtable Column Name`` to a model field called ``model_field_name``. Use this option if your Airtable column name and your model field name are different.
    * An ``AIRTABLE_SERIALIZER`` that takes a string path to your serializer. This helps map incoming data from Airtable to your model fields. Django Rest Framework is required for this. See the [examples/](examples/) directory for serializer examples.

* Lastly make sure you enable wagtail-airtable with ``WAGTAIL_AIRTABLE_ENABLED = True``. By default this is disabled so data in your Wagtail site and your Airtable sheets aren't accidentally overwritten. Data is hard to recover, this option helps prevent accidental data loss.

**************************
Example Base Configuration
**************************

Below is a base configuration or ``ModelName`` and ``OtherModelName`` (both are registered Wagtail snippets), along with ``HomePage``.

.. code-block:: python

    # your settings.py
    AIRTABLE_API_KEY = 'yourSuperSecretKey'
    WAGTAIL_AIRTABLE_ENABLED = True
    AIRTABLE_IMPORT_SETTINGS = {
        'appname.ModelName': {
            'AIRTABLE_BASE_KEY': 'app3ds912jFam032S',
            'AIRTABLE_TABLE_NAME': 'Your Airtable Table Name',
            'AIRTABLE_UNIQUE_IDENTIFIER': 'slug', # Must match the Airtable Column name
            'AIRTABLE_SERIALIZER': 'path.to.your.model.serializer.CustomModelSerializer'
        },
        'appname.OtherModelName': {
            'AIRTABLE_BASE_KEY': 'app4ds902jFam035S',
            'AIRTABLE_TABLE_NAME': 'Your Airtable Table Name',
            'AIRTABLE_UNIQUE_IDENTIFIER': {
                'Page Slug': 'slug', # 'Page Slug' column name in Airtable, 'slug' field name in Wagtail.
            },
            'AIRTABLE_SERIALIZER': 'path.to.your.model.serializer.OtherCustomModelSerializer'
        },
        'pages.HomePage': {
            'AIRTABLE_BASE_KEY': 'app2ds123jP23035Z',
            'AIRTABLE_TABLE_NAME': 'Wagtail Page Tracking Table',
            'AIRTABLE_UNIQUE_IDENTIFIER': {
                'Wagtail Page ID': 'pk',
            },
            'AIRTABLE_SERIALIZER': 'path.to.your.pages.serializer.PageSerializer',
            # Below are OPTIONAL settings.
            # By disabling `AIRTABLE_IMPORT_ALLOWED` you can prevent Airtable imports
            # Use cases may be:
            #   - disabling page imports since they are difficult to setup and maintain,
            #   - one-way sync to Airtable only (ie. when a model/Page is saved)
            # Default is True
            'AIRTABLE_IMPORT_ALLOWED': False,
            # Add the AIRTABLE_BASE_URL setting if you would like to provide a nice link
            # to the Airtable Record after a snippet or Page has been saved.
            # To get this URL open your Airtable base on Airtable.com and paste the link.
            # The recordId will be automatically added so please don't add that
            # You can add the below setting. This is optional and disabled by default.
            'AIRTABLE_BASE_URL': 'https://airtable.com/tblxXxXxXxXxXxXx/viwxXxXxXxXxXxXx',
        },
        # ...
    }

`View the repo README for more details <https://github.com/wagtail/wagtail-airtable/>`_
