from django.utils.translation import gettext_lazy
from ovinc_client.core.models import TextChoices


class FileUploadPurpose(TextChoices):
    EXTRACT = "file-extract", gettext_lazy("File Extract")
