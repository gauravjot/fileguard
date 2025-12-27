from django.contrib import admin
from .models import EncryptedFile, Directory


# Customize EncruptedFile admin interface
class EncryptedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'upload_date', 'status', 'directory', 'mark_deleted')
    list_filter = ('status', 'mark_deleted', 'upload_date')
    search_fields = ('original_filename',)
    ordering = ('-upload_date',)


admin.site.register(EncryptedFile, EncryptedFileAdmin)


# Customize Directory admin interface
class DirectoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_on', 'parent', 'mark_deleted')
    list_filter = ('mark_deleted', 'created_on')
    search_fields = ('name',)
    ordering = ('-created_on',)


admin.site.register(Directory, DirectoryAdmin)
