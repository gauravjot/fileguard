import os
import json
from django.db import models
from django.core import serializers


class Directory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='subdirectories', blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_contents(self):
        """
        Returns a list of files and subdirectories in this directory.
        """
        files = EncryptedFile.objects.filter(directory=self)
        subdirs = self.__class__.objects.filter(parent=self)
        return {
            'files': files,
            'subdirectories': subdirs
        }

    def get_descendants(self):
        """
        Returns a list of all subdirectories in this directory and its subdirectories.
        """
        descendants = []
        subdirs = self.__class__.objects.filter(parent=self)
        for subdir in subdirs:
            descendants.append(subdir)
            descendants.extend(subdir.get_descendants())
        return descendants

    def get_breadcrumbs(self) -> list[dict]:
        """
        Returns a list of directories from the root to this directory.
        """
        breadcrumbs = []
        current = self
        while current:
            breadcrumbs.append({'name': current.name, 'id': current.pk})
            current = current.parent
        # Add '/' for the root directory
        breadcrumbs.append({'name': 'Home', 'id': 0})
        return breadcrumbs[::-1]

    def move_to(self, new_parent):
        if self.parent == new_parent:
            return
        if new_parent is not None and new_parent == self:
            raise ValueError("Cannot move a directory to itself")
        # Check if the new parent is a subdirectory of the current directory
        if new_parent is not None and new_parent in self.get_descendants():
            raise ValueError("Cannot move a directory into one of its own subdirectories")
        # Update the parent directory
        self.parent = new_parent
        self.save()

    def create(self, name, parent=None):
        """
        Create a new directory with the given name and optional parent.
        """
        if not name:
            raise ValueError("Directory name cannot be empty")
        # Check if a directory with the same name already exists in the parent directory
        if parent:
            if super().objects.filter(name=name, parent=parent).exists():
                raise ValueError(f"Directory '{name}' already exists in the specified parent directory")
        else:
            if super().objects.filter(name=name, parent__isnull=True).exists():
                raise ValueError(f"Directory '{name}' already exists at the root level")
        return super().objects.create(name=name, parent=parent)

    def delete(self, *args, **kwargs):
        # Delete all files in this directory before deleting the directory itself
        files = EncryptedFile.objects.filter(directory=self)
        if files.exists():
            for file in files:
                file.delete()
        # Now delete the directory
        return super().delete(*args, **kwargs)


class EncryptedFile(models.Model):
    original_filename = models.CharField(max_length=255)
    encrypted_file = models.FileField(upload_to='encrypted_files/', blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(help_text="Size of the encrypted file in bytes")
    original_file_size = models.BigIntegerField(help_text="Size of the original file in bytes", blank=True, null=True)
    is_encrypted = models.BooleanField(default=True)
    # if blank, file is in root directory
    directory = models.ForeignKey(Directory, on_delete=models.CASCADE, related_name='files', blank=True, null=True)
    # Store salt and nonce for decryption (they are not secret)
    salt = models.BinaryField(max_length=16, blank=True, null=True)  # For PBKDF2
    nonce = models.BinaryField(max_length=16, blank=True, null=True)  # For AES-GCM (PyCryptodome's default)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True,
                                      help_text="Celery task ID for encryption/decryption")
    status = models.CharField(max_length=50, default='PENDING',
                              choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'),
                                       ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('DECRYPTING', 'Decrypting'), ('DECRYPTED', 'Decrypted')])
    decrypted_temp_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.original_filename

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('dashboard:download_encrypted', args=[str(self.pk)])

    def get_decryption_url(self):
        from django.urls import reverse
        return reverse('dashboard:decrypt_file', args=[str(self.pk)])

    def delete(self, *args, **kwargs):
        # Delete the actual file when the model instance is deleted
        if self.encrypted_file:
            if os.path.isfile(self.encrypted_file.path):
                os.remove(self.encrypted_file.path)
        # Also delete the temporary decrypted file if it exists and model is deleted
        if self.decrypted_temp_path and os.path.exists(self.decrypted_temp_path):
            os.remove(self.decrypted_temp_path)
        return super().delete(*args, **kwargs)

    def serialize(self, format='json'):
        """
        Serialize the EncryptedFile instance to the specified format.
        Default is JSON.
        """
        data = serializers.serialize(format, [self], use_natural_primary_keys=True, fields=(
            'original_filename', 'upload_date', 'file_size', 'original_file_size', 'is_encrypted', 'directory', 'celery_task_id', 'status'))
        if format == 'json':
            return json.loads(data)[0]
        return data


def get_home_contents(directory: str = '', sort: str = 'date') -> dict:
    """Get contents of the home directory, which includes all files and subdirectories.

    Returns:
        dict: A dictionary containing the subdirectories and files in the home directory.
    """
    if directory is '' or directory is '0':
        subdirs = Directory.objects.filter(parent=None)
        files = EncryptedFile.objects.filter(directory=None)
        parent_directory = None
    else:
        directory_id_parsed = int(directory)
        directory_obj = Directory.objects.filter(pk=directory_id_parsed).first()
        if not directory_obj:
            raise ValueError(f"Directory with ID {directory_id_parsed} does not exist.")
        contents = directory_obj.get_contents()
        subdirs = contents['subdirectories']
        files = contents['files']
        parent_directory = directory_obj.parent.pk if directory_obj.parent else '0'
    # Sort subdirectories and files based on the provided sort parameter
    if sort == 'name':
        subdirs = subdirs.order_by('name')
        files = files.order_by('original_filename')
    elif sort == 'date':
        subdirs = subdirs.order_by('-created_on')
        files = files.order_by('-upload_date')
    # transformations on files
    files = list(files)
    result_files = []
    for file in files:
        file_row = {'extension': file.original_filename.split(
            '.')[-1].lower() if '.' in file.original_filename else 'unknown', **file.__dict__}
        result_files.append(file_row)
    return {
        'subdirectories': subdirs,
        'files': result_files,
        'current_directory': directory if directory and len(directory) > 0 and int(directory) > 0 else None,
        'parent_directory': parent_directory
    }
