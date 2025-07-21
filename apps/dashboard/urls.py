from django.urls import path, re_path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    re_path('files/(?P<directory>.*)$', views.list_encrypted_files, name='list_encrypted_files'),
    path('file/<int:file_id>/', views.list_file_item, name='list_file_item'),
    path('download/encrypted/<int:file_id>/', views.download_encrypted_file, name='download_encrypted'),
    path('decrypt/<int:file_id>/', views.decrypt_file, name='decrypt_file'),
    path('task_status/<int:file_id>/', views.check_task_status, name='check_task_status'),
    path('download/<int:file_id>/', views.download_decrypted_file, name='download_decrypted_file'),

    # forms
    path('create_directory_form/', views.create_directory_form, name='create_directory_form'),
    path('upload_file_form/', views.upload_file_form, name='upload_file_form'),
]
