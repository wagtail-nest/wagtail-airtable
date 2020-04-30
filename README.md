# Wagtail/Airtable

An extension for Wagtail allowing content to be transferred between Airtable sheets and your Wagtail/Django models.

Developed by [Torchbox](https://torchbox.com/) and sponsored by [The Motley Fool](https://www.fool.com/).

TODO: Create an animation demonstrating how it works.

### How it works

When you setup a model to "map" to an Airtable sheet, everytime you save the model it will attempt to update the row in Airtable. If a row is not found, it will create a new row in your Airtable.

When you want to sync your Airtable data to your Wagtail website, you can go to `Settings -> Airtable Import`. You can then import entire tables into your Wagtail instance with the click of a button. If you see "_{Your Model}_ is not setup with the correct Airtable settings" you will need to double check your settings.

##### Behind the scenes...
This package will attempt to match a model object against row in Airtable using a `record_id`. If a model does not have a record_id value, it will look for a match using the `AIRTABLE_UNIQUE_IDENTIFIER` to try and match a unique value in the Airtable to the unique value in your model. Should that succeed your model object will be "paired" with the row in Airtable. But should the record-search fail, a new row in Airtable will be created when you save your model, or a new model object will attempt to be created when you import a model from Airtable.

> **Note**: Object creation _can_ fail when importing from Airtable. This is expected behaviour as an Airtable might not have all the data a model requires. For instance, a Wagtail Page uses Django Tree Beard and if a `path` is not in the model import settings (and a column in Airtable) a page cannot be created. Or if Airtable doesn't have a column for a required field on a Django Model, it won't be created.

### Installation & Configuration

* Install the package with `pip install wagtail-airtable`
* Add `'wagtail_airtable'` to your project's `INSTALLED_APPS`
* In your settings you will need to map models to Airtable settings. Every model you want to map to an Airtable sheet will need:
    * An `AIRTABLE_BASE_KEY`. You can find the base key in your Airtable docs when you're signed in to Airtable.com
    * An `AIRTABLE_TABLE_NAME` to determine which table to connect to.
    * An `AIRTABLE_UNIQUE_IDENTIFIER`. This can either be a string or a dictionary mapping the Airtable column name to your unique field in your model.
        * ie. `AIRTABLE_UNIQUE_IDENTIFIER: 'slug',` this will match the `slug` field on your model with the `slug` column name in Airtable. Use this option if your model field and your Airtable column name are identical.
        * ie. `AIRTABLE_UNIQUE_IDENTIFIER: {'Airtable Column Name': 'model_field_name'},` this will map the `Airtable Column Name` to a model field called `model_field_name`. Use this option if your Airtable column name and your model field name are different.
    * An `AIRTABLE_SERIALIZER` that takes a string path to your serializer. This helps map incoming data from Airtable to your model fields. Django Rest Framework is required for this. See the [examples/](examples/) directory for serializer examples.
* Add the following to your `urls.py`:
    ```python
    from django.urls import path
    from wagtail_airtable.views import AirtableImportListing
    ...
    urlpatterns = [
        ...
        path("airtable-import", AirtableImportListing.as_view(), name="airtable_import_listing"),
    ]
    ```

* Lastly make sure you enable wagtail-airtable with `WAGTAIL_AIRTABLE_ENABLED = True`. By default this is disabled so data in your Wagtail site and your Airtable sheets aren't accidentally overwritten. Data is hard to recover, this option helps prevent accidental data loss.

### Example Base Configuration

```python
# your settings.py
WAGTAIL_AIRTABLE_ENABLED = True
AIRTABLE_IMPORT_SETTINGS = {
    'appname.ModelName': {
        'AIRTABLE_BASE_KEY': 'app3ds912jFam032S',
        'AIRTABLE_TABLE_NAME': 'Your Airtable Table Name',
        'AIRTABLE_UNIQUE_IDENTIFIER': 'slug', # Must match the Airtable Column name
        'AIRTABLE_SERIALIZER': 'path.to.your.model.serializer.CustomModelSerializer'
    },
    'appname.OtherModelName': {
        'AIRTABLE_BASE_KEY': 'app3ds912jFam032S',
        'AIRTABLE_TABLE_NAME': 'Your Airtable Table Name',
        'AIRTABLE_UNIQUE_IDENTIFIER':
            'Page Slug': 'slug', # 'Page Slug' column name in Airtable, 'slug' field name in Wagtail.
        },
        'AIRTABLE_SERIALIZER': 'path.to.your.model.serializer.OtherCustomModelSerializer'
    },
    # ...
}
```

### Management Commands

```bash
python manage.py import_airtable appname.ModelName secondapp.SecondModel
```

Optionally you can turn up the verbosity for better debugging with the `--verbosity=2` flag.

##### import_airtable command
This command will look for any `appname.ModelName`s you provide it and use the mapping settings to find data in the Airtable. See the "Behind the scenes" section for more details on how importing works.

### Local Testing Advice

> **Note:** Careful not to use the production settings as you could overwrite Wagtail or Airtable data.

Because Airtable doesn't provide a testing environment, you'll need to test against a live table. The best way to do this is to copy your live table to a new table (renaming it will help avoid naming confusion), and update your local settings. With this method, you can test to everything safely against a throw-away Airtable. Should something become broken beyond repair, delete the testing table and re-copy the original one.

### Local debugging
Due to the complexity and fragility of connecting Wagtail and Airtable (because an Airtable column can be almost any value) you may need some help debugging your setup. To turn on higher verbosity output, you can enable the Aritable debug setting `WAGTAIL_AIRTABLE_DEBUG = True`. All this does is increase the default verbosity when running the management command. In a standard Django management command you could run `python manage.py import_airtable appname.ModelName --verbosty=2` however when you import from Airtable using the Wagtail admin import page you won't have access to this verbosity argument. But enabling `WAGTAIL_AIRTABLE_DEBUG` you can manually increase the verbosity.

> **Note**: This only only work while `DEBUG = True` in your settings as to not accidentally flood your production logs.
