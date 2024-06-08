import os

from channels.consumer import AsyncConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from django.utils.module_loading import import_string

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entry.settings")


def to_asgi(consumer_path: str) -> AsyncConsumer:
    cls = import_string(consumer_path)
    return cls.as_asgi()


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(
            [
                path("chat/", to_asgi("apps.chat.consumers.ChatConsumer")),
            ]
        ),
    }
)
