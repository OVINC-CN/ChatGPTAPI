from django.utils.translation import gettext_lazy
from ovinc_client.core.models import TextChoices

FILE_CONTENT_CACHE_KEY = "file_content:{file_path_sha256}"
FILE_UPLOAD_CACHE_KEY = "file_upload:{key}"


class FileUploadPurpose(TextChoices):
    EXTRACT = "file-extract", gettext_lazy("File Extract")
