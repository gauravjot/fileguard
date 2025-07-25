from django.shortcuts import render, redirect

# Create your views here.


def home_page(request):
    # Send to login page
    return redirect('login')


def login_page(request):
    return render(request, 'login.html')


def setup_page(request):
    return render(request, 'setup.html')
