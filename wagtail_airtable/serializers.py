from rest_framework import serializers


class AirtableSerializer(serializers.Serializer):
    """
    Generic Airtable serializer for parsing Airtable API JSON data into proper model data.
    """

    def validate(self, data):
        """
        Loop through all the values, and if anything comes back as 'None' return an empty string.

        Not all fields will have cleaned data. Some fields could be stored as 'None' in Airtable,
        so we need to loop through every value and converting 'None' to ''
        """
        for key, value in data.items():
            # If any fields pass validation with the string 'None', return a blank string
            if value == "None":
                data[key] = ""
        return data
