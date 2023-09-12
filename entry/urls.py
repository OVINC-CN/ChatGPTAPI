from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from ovinc_client.core import exceptions

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=f"{settings.FRONTEND_URL}/favicon.ico")),
    path("admin/", admin.site.urls),
    path("account/", include("ovinc_client.account.urls")),
    path("", include("apps.home.urls")),
    path("", include("apps.chat.urls")),
    path("", include("ovinc_client.trace.urls")),
]

handler400 = exceptions.bad_request
handler403 = exceptions.permission_denied
handler404 = exceptions.page_not_found
handler500 = exceptions.server_error
