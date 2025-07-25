from django import forms
from .util.auth import verify_totp


class SetupAuthForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)
    otp_secret = forms.CharField(
        help_text="Enter this value in your authenticator app or scan the QR code below.", required=True)
    otp_code = forms.IntegerField(
        label="One-Time Password Code",
        help_text="Enter the code generated by your authenticator app.",
        required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate a new OTP secret for the form
        self.fields['otp_secret'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        otp_code = cleaned_data.get("otp_code")
        otp_secret = cleaned_data.get("otp_secret")

        if not otp_code or not otp_secret:
            raise forms.ValidationError("OTP code and secret are required.")

        if verify_totp(otp_secret, otp_code) is False:
            raise forms.ValidationError("Invalid OTP code.")

        if not password or not confirm_password:
            raise forms.ValidationError("Both password fields are required.")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        if password and len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")

        return cleaned_data
