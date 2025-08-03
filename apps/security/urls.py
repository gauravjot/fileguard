from django.urls import path

from . import views

app_name = 'security'

urlpatterns = [
    path('', views.login_page, name='home'),
    path('login/', views.login_page, name='login'),
    path('setup/', views.setup_page, name='setup'),
    path('logout/', views.logout_page, name='logout')
]
