import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entry.settings")
django_app = get_asgi_application()

# pylint: disable=C0413
from apps.chat.consumers import ChatConsumer

application = ProtocolTypeRouter(
    {
        "http": django_app,
        "websocket": URLRouter(
            [
                path("chat/", ChatConsumer.as_asgi()),
            ]
        ),
    }
)
