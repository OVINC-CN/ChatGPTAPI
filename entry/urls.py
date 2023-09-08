from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core import exceptions

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=f"{settings.FRONTEND_URL}/favicon.ico")),
    path("admin/", admin.site.urls),
    path("", include("apps.home.urls")),
    path("", include("apps.chat.urls")),
    path("", include("apps.trace.urls")),
]

handler400 = exceptions.bad_request
handler403 = exceptions.permission_denied
handler404 = exceptions.page_not_found
handler500 = exceptions.server_error
