## Known Issues and work arounds
> All of these would make amazing PR's ;)

#### Decimal Fields
- [ ] In `get_export_fields()` if you map a decimal field you'll need to convert it to a string for it to be JSONified and for Airtable to accept it. ie:
    ```python
    rating = models.DecimalField(...)

    def get_export_fields(..):
        return {
            ...
            "rating": str(self.rating) if self.rating else None,
        }
    ```
