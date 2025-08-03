from django.db import models
from django.utils.timezone import now
from .managers import SessionManager

# Create your models here.


class Session(models.Model):
    key = models.CharField(max_length=64)
    is_valid = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)
    expire_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    manage = SessionManager()

    def __str__(self):
        return f"{self.pk}"
