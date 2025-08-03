from django.shortcuts import render, redirect
from .forms import SetupAuthForm, LoginForm
from .util.auth import config_auth, generate_otp_secret, is_pass_file_present
from .models import Session
from .permissions import is_authenticated


def login_page(request):
    if is_pass_file_present():
        form = LoginForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            # is_valid() process the authentication, now we set a session cookie
            response = redirect('dashboard:index')
            key, session = Session.manage.create_session(request)
            if not session:
                form.add_error(None, "Session creation failed. Please try again.")
                return render(request, 'login.html', {'form': form})
            response.set_cookie(
                key='fileguard_session',
                value=key,
                expires=session.expire_at,
                httponly=True,
                secure=True,
                samesite='Lax',
                domain=request.get_host().split(':')[0]
            )
            # redirect to dashboard
            return response
        return render(request, 'login.html', {'form': form})
    else:
        return redirect('security:setup')


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


@is_authenticated()
def logout_page(request):
    if request.method != "POST":
        return redirect('dashboard:index')
    response = redirect('security:login')
    # Clear the session cookie
    response.delete_cookie('fileguard_session', domain=request.get_host().split(':')[0])
    session = request.active_session
    if session:
        Session.manage.delete_session(session.id)
    return response
