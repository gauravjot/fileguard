from django.urls import path, re_path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_encrypt_file, name='upload_encrypt_file'),
    re_path('files/(?P<directory>.*)$', views.list_encrypted_files, name='list_encrypted_files'),
    path('download/encrypted/<int:file_id>/', views.download_encrypted_file, name='download_encrypted'),
    path('decrypt/<int:file_id>/', views.decrypt_file, name='decrypt_file'),
    path('task_status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('download/<int:file_id>/', views.download_decrypted_file, name='download_decrypted_file'),
    path('create_directory/', views.create_directory, name='create_directory'),

    # forms
    path('create_directory_form/<str:parent_directory>/', views.create_directory_form, name='create_directory_form'),
]