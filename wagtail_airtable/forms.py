from django import forms
from django.conf import settings


class AirtableImportModelForm(forms.Form):

    model = forms.CharField()

    def clean_model(self):
        """Make sure this model is in the AIRTABLE_IMPORT_SETTINGS config."""

        model_label = self.cleaned_data["model"].lower()
        airtable_settings = getattr(settings, "AIRTABLE_IMPORT_SETTINGS", {})
        is_valid_model = False

        for label, model_settings in airtable_settings.items():
            if model_label == label.lower():
                is_valid_model = True
                break

        if not is_valid_model:
            raise forms.ValidationError("You are importing an unsupported model")

        return model_label
