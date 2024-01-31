# Wagtail/Airtable

An extension for Wagtail allowing content to be transferred between Airtable sheets and your Wagtail/Django models.

Developed by [Torchbox](https://torchbox.com/) and sponsored by [The Motley Fool](https://www.fool.com/).

![Wagtail Airtable demo](examples/preview.gif)

### How it works

When you setup a model to "map" to an Airtable sheet, every time you save the model it will attempt to update the row in Airtable. If a row is not found, it will create a new row in your Airtable.

When you want to sync your Airtable data to your Wagtail website, you can go to `Settings -> Airtable Import`. You can then import entire tables into your Wagtail instance with the click of a button. If you see "_{Your Model}_ is not setup with the correct Airtable settings" you will need to double check your settings. By default the import page can be found at http://yourwebsite.com/admin/airtable-import/, or if you use a custom /admin/ url it'll be http://yourwebsite.com/{custom_admin_url}/airtable-import/.

##### Behind the scenes...
This package will attempt to match a model object against row in Airtable using a `record_id`. If a model does not have a record_id value, it will look for a match using the `AIRTABLE_UNIQUE_IDENTIFIER` to try and match a unique value in the Airtable to the unique value in your model. Should that succeed your model object will be "paired" with the row in Airtable. But should the record-search fail, a new row in Airtable will be created when you save your model, or a new model object will attempt to be created when you import a model from Airtable.

> **Note**: Object creation _can_ fail when importing from Airtable. This is expected behaviour as an Airtable might not have all the data a model requires. For instance, a Wagtail Page uses django-treebeard, with path as a required field. If the page model import settings do not include the path field, or a path column isn't present in Airtable, the page cannot be created. This same rule applies to other required fields on any Django model including other required fields on a Wagtail Page.

### Installation & Configuration

* Install the package with `pip install wagtail-airtable`
* Add `'wagtail_airtable'` to your project's `INSTALLED_APPS`.
    * On Wagtail 5.x, to enable the snippet-specific import button on the Snippet list view make sure `wagtail_airtable` is above `wagtail.snippets` in your `INSTALLED_APPS`
* In your settings you will need to map Django models to Airtable settings. Every model you want to map to an Airtable sheet will need:
    * An `AIRTABLE_BASE_KEY`. You can find the base key in the [Airtable API docs](https://airtable.com/api) when you're signed in to Airtable.com
    * An `AIRTABLE_TABLE_NAME` to determine which table to connect to.
    * An `AIRTABLE_UNIQUE_IDENTIFIER`. This can either be a string or a dictionary mapping the Airtable column name to your unique field in your model.
        * ie. `AIRTABLE_UNIQUE_IDENTIFIER: 'slug',` this will match the `slug` field on your model with the `slug` column name in Airtable. Use this option if your model field and your Airtable column name are identical.
        * ie. `AIRTABLE_UNIQUE_IDENTIFIER: {'Airtable Column Name': 'model_field_name'},` this will map the `Airtable Column Name` to a model field called `model_field_name`. Use this option if your Airtable column name and your model field name are different.
    * An `AIRTABLE_SERIALIZER` that takes a string path to your serializer. This helps map incoming data from Airtable to your model fields. Django Rest Framework is required for this. See the [examples/](examples/) directory for serializer examples.

* Lastly make sure you enable wagtail-airtable with `WAGTAIL_AIRTABLE_ENABLED = True`. By default this is disabled so data in your Wagtail site and your Airtable sheets aren't accidentally overwritten. Data is hard to recover, this option helps prevent accidental data loss.

### Example Base Configuration

Below is a base configuration or `ModelName` and `OtherModelName` (both are registered Wagtail snippets), along with `HomePage`.

```python
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
        'AIRTABLE_IMPORT_ALLOWED': True,
        # Add the AIRTABLE_BASE_URL setting if you would like to provide a nice link
        # to the Airtable Record after a snippet or Page has been saved.
        # To get this URL open your Airtable base on Airtable.com and paste the link.
        # The recordId will be automatically added so please don't add that
        # You can add the below setting. This is optional and disabled by default.
        'AIRTABLE_BASE_URL': 'https://airtable.com/tblxXxXxXxXxXxXx/viwxXxXxXxXxXxXx',
        # The PARENT_PAGE_ID setting is used for creating new Airtable Pages. Every
        # Wagtail Page requires a "parent" page. This setting can either be:
        # 1. A callable (ie `my_function` without the parentheses)'
        # Example:
        # 'PARENT_PAGE_ID': custom_function,
        # 2. A path to a function. (ie. 'appname.directory.filename.my_function')
        # Example:
        # 'PARENT_PAGE_ID': 'path.to.function',
        # 3. A raw integer.
        # Example:
        # 'PARENT_PAGE_ID': 3,

        # If you choose option #1 (callable) or option #2 (path to a function)
        # Your function needs to return an integer which will represent the Parent
        # Page ID where all imported pages will be created as child pages.
        # Callables and path-to-functions (option #1 and option #2 in the above docs)
        # Take an `instance` kwarg as of v0.2.1. Example below:
        #   def custom_parent_page_id_function(instance=None):
        #       if instance and isinstance(instance, Page):
        #           return Page.objects.get(pk=instance.id).get_parent()
        'PARENT_PAGE_ID': 'path.to.function',
        # The `AUTO_PUBLISH_NEW_PAGES` setting will tell this package to either
        # Automatically publish a newly created page, or set to draft.
        # True = auto publishing is on. False = auto publish is off (pages will be drafts)
        'AUTO_PUBLISH_NEW_PAGES': False,
    },
    # ...
}
```

##### Have multiple models with the same Airtable settings?
The most common approach will likely be to support a handful of models, in which case using the below example would be faster and cleaner. Write a config dictionary once to prevent config bloat.

```python
AIRTABLE_API_KEY = 'yourSuperSecretKey'
WAGTAIL_AIRTABLE_ENABLED = True
CUSTOM_PAGE_SETTINGS = {
    'AIRTABLE_BASE_KEY': 'app3ds912jFam032S',
    'AIRTABLE_TABLE_NAME': 'Your Airtable Table Name',
    'AIRTABLE_UNIQUE_IDENTIFIER': 'slug', # Must match the Airtable Column name
    'AIRTABLE_SERIALIZER': 'path.to.your.model.serializer.CustomModelSerializer'
},
AIRTABLE_IMPORT_SETTINGS = {
    'home.HomePage': CUSTOM_PAGE_SETTINGS,
    'blog.BlogPage': CUSTOM_PAGE_SETTINGS,
    'appname.YourModel': CUSTOM_PAGE_SETTINGS,
}
```

### Wagtail Page creation on Airtable Imports

This feature was sponsored by [The Mozilla Foundation](https://foundation.mozilla.org/).

In `wagtail-airtable` v0.1.6 and up you can create Wagtail Pages from Airtable imports.

A few settings need to be set for this to work as you would expect. Read through the following code to see which settings are needed:

```python
AIRTABLE_IMPORT_SETTINGS = {
    'pages.HomePage': {
        'AIRTABLE_BASE_KEY': 'app2ds123jP23035Z',
        'AIRTABLE_TABLE_NAME': 'Wagtail Page Tracking Table',
        'AIRTABLE_UNIQUE_IDENTIFIER': {
            'Wagtail Page ID': 'pk',
        },
        'AIRTABLE_SERIALIZER': 'path.to.your.pages.serializer.PageSerializer',
        'AIRTABLE_IMPORT_ALLOWED': True,  # This must be set
        'PARENT_PAGE_ID': 'path.to.function.that.returns.an.integer',  # This must be set
    },
}
```

Once your settings are ready, you can start creating new Pages in Airtable and import those pages via the Wagtail Admin (found in the setting menu).

**Caveats**: In the above code we see `{'Wagtail Page ID': 'pk',}`, this means there's a column in Airtable named "Wagtail Page ID" and it mapped to a Page pk. When you create a new Wagtail Page inside of an Airtable sheet, _keep this cell blank in your new row_. It will auto-update when it gets imported. This happens because Airtable (and the editors) likely don't know what the new Page ID is going to be, so we let Wagtail set it, and then update the Airtable again.

### Hooks
Hooks are a way to execute code once an action has happened. This mimics (and internally uses) Wagtail's hook feature.

> **Note**: When using hooks it will add processing time to your requests. If you're using Heroku with a 30s timeout you may want to use a management command to avoid hitting a server timeout.

##### Updated record
To take an action when a record is updated, you can write a hook like this in your wagtail_hooks.py file:

```python
@hooks.register('airtable_import_record_updated')
def airtable_record_updated(instance, is_wagtail_page, record_id):
    # Instance is the page or model instance
    # is_wagtail_page is a boolean to determine if the object is a wagtail page. This is a shortcut for `isinstance(instance, wagtail.models.Page)`
    # record_id is the wagtail record ID. You can use this to perform additional actions against Airtable using the airtable-python-wrapper package.
    pass
```

### Management Commands

```bash
python manage.py import_airtable appname.ModelName secondapp.SecondModel
```

Optionally you can turn up the verbosity for better debugging with the `--verbosity=2` flag.

##### import_airtable command
This command will look for any `appname.ModelName`s you provide it and use the mapping settings to find data in the Airtable. See the "Behind the scenes" section for more details on how importing works.

##### skipping django signals
By default the `import_airtable` command adds an additional attribute to the models being saved called `_skip_signals` - which is set to `True` you can use this to bypass any `post_save` or `pre_save` signals you might have on the models being imported so those don't run. e.g.

```
@receiver(post_save, sender=MyModel)
def post_save_function(sender, **kwargs):
    if sender._skip_signals:
        # rest of logic
```

if you don't do these checks on your signal, the save will run normally.

### Local Testing Advice

> **Note:** Be careful not to use the production settings as you could overwrite Wagtail or Airtable data.

Because Airtable doesn't provide a testing environment, you'll need to test against a live table. The best way to do this is to copy your live table to a new table (renaming it will help avoid naming confusion), and update your local settings. With this method, you can test to everything safely against a throw-away Airtable. Should something become broken beyond repair, delete the testing table and re-copy the original one.

### Local debugging
Due to the complexity and fragility of connecting Wagtail and Airtable (because an Airtable column can be almost any value) you may need some help debugging your setup. To turn on higher verbosity output, you can enable the Airtable debug setting `WAGTAIL_AIRTABLE_DEBUG = True`. All this does is increase the default verbosity when running the management command. In a standard Django management command you could run `python manage.py import_airtable appname.ModelName --verbosity=2` however when you import from Airtable using the Wagtail admin import page you won't have access to this verbosity argument. But enabling `WAGTAIL_AIRTABLE_DEBUG` you can manually increase the verbosity.

> **Note**: This only only work while `DEBUG = True` in your settings as to not accidentally flood your production logs.

### Airtable Best Practice
Airtable columns can be one of numerous "types", very much like a Python data type or Django field. You can have email columns, url columns, single line of text, checkbox, etc.

To help maintain proper data synchronisation between your Django/Wagtail instance and your Airtable Base's, you _should_ set the column types to be as similar to your Django fields as possible.

For example, if you have a BooleanField in a Django model (or Wagtail Page) and you want to support pushing that data to Airtable amd support importing that same data from Airtable, you should set the column type in Airtable to be a Checkbox (because it can only be on/off, much like how a BooleanField can only be True/False).

In other cases such as Airtables Phone Number column type: if you are using a 3rd party package to handle phone numbers and phone number validation, you'll want to write a custom serializer to handle the incoming value from Airtable (when you import from Airtable). The data will likely come through to Wagtail as a string and you'll want to adjust the string value to be a proper phone number format for internal Wagtail/Django storage. (You may also need to convert the phone number to a standard string when exporting to Airtable as well)

### Running Tests
Clone the project and cd into the `wagtail-airtable/` directory. Then run `python runtests.py tests`. This project is using standard Django unit tests.

To target a specific test you can run `python runtests.py tests.test_file.TheTestClass.test_specific_model`

Tests are written against Wagtail 2.10 and later.

### Customizing the save method
In some cases you may want to customize how saving works, like making the save to airtable asynchronous for example.

To do so, set: WAGTAIL_AIRTABLE_SAVE_SYNC=False in your settings.py file. 

This _escapes_ out of the original save method and requires you enable the asynchronous part of this on your own.

An example of how you might set this up using the signal `after_page_publish` with [django_rq](https://github.com/rq/django-rq)
```
#settings.py
WAGTAIL_AIRTABLE_SAVE_SYNC=False
WAGTAIL_AIRTABLE_PUSH_MESSAGE="Airtable save happening in background"

#wagtail_hooks.py
from django.dispatch import receiver
from wagtail.models import Page

@job('airtable')
def async_airtable_save(page_id):
    my_page = Page.objects.get(page_id).specific
    my_page.save_to_airtable()
    
    
@receiver('page_published')
def upload_page_to_airtable(request, page):
    async_airtable_save.delay(page.pk)

```


The messaging will be off if you do this, so another setting has been made available so you may change the messaging to anything you'd like:
`WAGTAIL_AIRTABLE_PUSH_MESSAGE` - set this to whatever you'd like the messaging to be e.g. `WAGTAIL_AIRTABLE_PUSH_MESSAGE='Airtable save is happening in the background'`


### Adding an Import action to the snippet list view (Wagtail 6.x)

As of Wagtail 6.0, the Import action is no longer automatically shown on the snippet listing view (although it is still available through Settings -> Airtable import). To add it back, first ensure that your snippet model is [registered with an explicit viewset](https://docs.wagtail.org/en/stable/topics/snippets/registering.html#using-register-snippet-as-a-function). Then, ensure that the index view for that viewset inherits from `SnippetImportActionMixin`:

```python
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import IndexView, SnippetViewSet
from wagtail_airtable.mixins import SnippetImportActionMixin
from .models import Advert


class AdvertIndexView(SnippetImportActionMixin, IndexView):
    pass


class AdvertViewSet(SnippetViewSet):
    model = Advert
    index_view_class = AdvertIndexView

register_snippet(Advert, viewset=AdvertViewSet)
```


### Trouble Shooting Tips
#### Duplicates happening on import
Ensure that your serializer matches your field definition *exactly*, and in cases of `CharField`'s that have `blank=True` or `null=True` setting `required=False` on the serializer is also important.

In some cases 2 Models may get the same Airtable ID. To circumvent this error on imports the first one found will be set as the "real" one and the "impostors" will be set to `""` - this may create duplicate models in your system, if this is happening a lot. Make sure your export method and serializer import are set correctly.
