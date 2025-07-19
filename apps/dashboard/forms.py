from django import forms


class EncryptFileForm(forms.Form):
    file = forms.FileField(
        label='Select a file to encrypt',
        help_text='Max. 50 MB (configurable in settings)'
    )
    password = forms.CharField(
        label='Encryption Password',
        widget=forms.PasswordInput,
        help_text='This password is used to encrypt your file. Keep it secret!'
    )
    # You might want to add a password confirmation field
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput
    )
    parent_directory = forms.IntegerField(
        label='Parent Directory',
        required=False,
        # hidden
        widget=forms.HiddenInput,
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data


class DecryptFileForm(forms.Form):
    password = forms.CharField(
        label='Decryption Password',
        widget=forms.PasswordInput,
        help_text='Enter the password used to encrypt this file.'
    )


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
