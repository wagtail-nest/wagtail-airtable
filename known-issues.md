## Known Issues and workarounds
> All of these would make amazing PR's ;)

#### Decimal Fields
In `get_export_fields()` if you map a decimal field you'll need to convert it to a string for it to be JSONified and for Airtable to accept it. ie:
```python
rating = models.DecimalField(...)

def get_export_fields(..):
    return {
        ...
        "rating": str(self.rating) if self.rating else None,
    }
```

#### Duplicate records by unique column value
If any operation needs to find a new Airtable record by its unique column name (and value) such as a `slug` or `id`, and multiple records are returned at the same time, wagtail-airtable will use the first available option that Airtable returns.

The problem with this lies in editing Airtable records. Because of this someone may edit the wrong record and the `import` function may not import the correct data.

Also Airtable does not need to return the records in order from first to last. For example, if you saved a model and it had 4 matched records in your Airtable because there were 4 cells with the slug of "testing-record-slug", you may not get the first record in the list of returned records. In several test cases there were random cases of the first, middle and last records being selected. This is more of an issue with Airtable not giving us all the records in proper order. Whichever record is found first is the record your Django object will be tied to moving forward.
