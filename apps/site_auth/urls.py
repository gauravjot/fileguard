from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('login/', views.login_page, name='login'),
    path('setup/', views.setup_page, name='setup'),
]
