import json
import logging

from daphne import server
from django.core.cache import cache
from django_redis.client import DefaultClient
from redis import Redis

from utils.prometheus.constants import PrometheusLabels, PrometheusMetrics
from utils.prometheus.exporters import PrometheusExporter

cache: DefaultClient
CONNECTION_CACHE_KEY = "websocket_connections"

logger = logging.getLogger(server.__name__)


class ConnectionsHandler:
    def __init__(self):
        self.redis: Redis = cache.client.get_client()

    def init_key(self) -> None:
        self.redis.delete(CONNECTION_CACHE_KEY)

    def add_connection(self, connection: str, client_ip: str) -> None:
        self.redis.hset(CONNECTION_CACHE_KEY, connection, client_ip)
        self.log_connection(desc="WebSocket CONNECT", connection=connection, client_ip=client_ip)

    def remove_connection(self, connection: str, client_ip: str) -> None:
        self.redis.hdel(CONNECTION_CACHE_KEY, connection)
        self.log_connection(desc="WebSocket DISCONNECT", connection=connection, client_ip=client_ip)

    def log_connection(self, desc: str, **kwargs) -> None:
        connections = self.connections_count()
        logger.info(
            "%s Connections: %d; Extra: %s",
            desc,
            connections,
            json.dumps(kwargs, ensure_ascii=False),
        )
        PrometheusExporter(
            name=PrometheusMetrics.WEBSOCKET_CONN,
            samples=[(None, connections)],
            labels=[(PrometheusLabels.HOSTNAME, PrometheusExporter.hostname())],
        ).export()

    def connections_count(self) -> int:
        return self.redis.hlen(CONNECTION_CACHE_KEY)


connections_handler = ConnectionsHandler()
