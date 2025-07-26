from django.shortcuts import render, redirect
from .forms import SetupAuthForm
from .util.auth import config_auth, generate_otp_secret, is_pass_file_present

# Create your views here.


def home_page(request):
    # Send to login page
    return redirect('login')


def login_page(request):
    return render(request, 'login.html')


def setup_page(request):
    if is_pass_file_present():
        return render(request, 'security/setup_already_done.html')
    form = SetupAuthForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Process the valid form data
        data = form.cleaned_data
        password = data.get('password')
        otp_code = data.get('otp_code')
        otp_secret = data.get('otp_secret')

        if not password or not otp_code or not otp_secret:
            form.add_error(None, "All fields are required.")
            return render(request, 'setup.html', {'form': form})

        try:
            backup_codes = config_auth(password, otp_secret, otp_code)
            # Redirect to success page or display a success message
            return render(request, 'security/setup_success.html', {'backup_codes': backup_codes})
        except Exception as e:
            form.add_error(None, f"An error occurred: {str(e)}")
    if request.method == "POST":
        # keep the same otp_secret if the form is invalid
        form.fields['otp_secret'].initial = form.data.get('otp_secret', generate_otp_secret())
    elif request.method == "GET":
        # Generate a new OTP secret for the form
        otp_secret = generate_otp_secret()
        form.fields['otp_secret'].initial = otp_secret
    return render(request, 'security/setup.html', {'form': form})
