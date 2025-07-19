from django.db import models


class DirectoryManager(models.Manager):
    def create_directory(self, name, parent=None):
        """
        Create a new directory with the given name and optional parent.
        """
        if not name:
            raise ValueError("Directory name cannot be empty")
        # Check if a directory with the same name already exists in the parent directory
        if parent:
            if self.filter(name=name, parent=parent).exists():
                raise ValueError(f"Directory '{name}' already exists in the specified parent directory")
        else:
            if self.filter(name=name, parent__isnull=True).exists():
                raise ValueError(f"Directory '{name}' already exists at the root level")
        directory = self.create(name=name, parent=parent)
        return directory
