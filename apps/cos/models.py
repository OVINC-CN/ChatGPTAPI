import hashlib

from django.db import models
from django.utils.translation import gettext_lazy
from ovinc_client.core.models import BaseModel


class FileExtractInfo(BaseModel):
    """
    File Extract Info
    """

    key = models.CharField(gettext_lazy("Key"), max_length=255, unique=True)
    file_path = models.TextField(gettext_lazy("File Path"))
    upload_info = models.JSONField(gettext_lazy("Upload Info"), null=True, blank=True)
    extract_info = models.JSONField(gettext_lazy("Extract Info"), null=True, blank=True)
    is_finished = models.BooleanField(gettext_lazy("Is Finished"), default=False, db_index=True)
    is_success = models.BooleanField(gettext_lazy("Is Success"), default=False, db_index=True)
    created_at = models.DateTimeField(gettext_lazy("Created At"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = gettext_lazy("File Extract Info")
        verbose_name_plural = verbose_name
        ordering = ["-id"]

    def __str__(self):
        return str(self.id)

    @classmethod
    def build_key(cls, file_path: str) -> str:
        return hashlib.sha256(file_path.encode()).hexdigest()
