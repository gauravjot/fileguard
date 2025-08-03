from django import forms


class EncryptFileForm(forms.Form):
    file = forms.FileField(
        label='Select a file to encrypt',
        help_text='Max. 50 MB (configurable in settings)'
    )
    parent_directory = forms.IntegerField(
        label='Parent Directory',
        required=False,
        # hidden
        widget=forms.HiddenInput,
    )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class CreateDirectoryForm(forms.Form):
    directory_name = forms.CharField(
        label='Directory Name',
        max_length=255,
        help_text='Name of the new directory to create.'
    )
    parent_directory = forms.IntegerField(
        label='Parent Directory',
        required=False,
        # hidden
        widget=forms.HiddenInput,
    )

    def clean_directory_name(self):
        directory_name = self.cleaned_data.get('directory_name')
        if not directory_name:
            raise forms.ValidationError("Directory name cannot be empty.")
        return directory_name
