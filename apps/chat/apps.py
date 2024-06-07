from django.apps import AppConfig
from django.db.models.signals import post_migrate


def reset_connection_cache(sender, **kwargs):
    # pylint: disable=C0415
    from utils.connections import ConnectionsHandler

    ConnectionsHandler().init_key()


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"

    def ready(self):
        post_migrate.connect(reset_connection_cache, sender=self)
