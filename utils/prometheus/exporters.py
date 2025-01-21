# pylint: disable=E1101,R0402
import os
import time
from typing import List, Tuple

import snappy
from django.conf import settings
from httpx import BasicAuth, Client
from ovinc_client.core.logger import logger

from utils.prometheus import prometheus_pb2

HOSTNAME_INIT = False
HOSTNAME = ""


class PrometheusExporter:
    """
    Prometheus exporter
    """

    def __init__(self, *, name: str, samples: List[Tuple[int | None, float]], labels: List[Tuple[str, str]]):
        self.name = name
        self.samples = samples
        self.labels = labels
        self.default_timestamp = self.current_ts()

    def export(self) -> None:
        if not settings.ENABLE_METRIC:
            return
        try:
            request = prometheus_pb2.WriteRequest(
                timeseries=[
                    prometheus_pb2.TimeSeries(
                        labels=[
                            prometheus_pb2.Label(name="__name__", value=self.name),
                            *[prometheus_pb2.Label(name=name, value=value) for name, value in self.labels],
                        ],
                        samples=[
                            prometheus_pb2.Sample(value=value, timestamp=ts or self.default_timestamp)
                            for ts, value in self.samples
                        ],
                    )
                ]
            )
            request_data = request.SerializeToString()
            with Client(http2=True) as client:
                response = client.post(
                    url=settings.PROMETHEUS_API,
                    auth=BasicAuth(settings.PROMETHEUS_API_USERNAME, settings.PROMETHEUS_API_PASSWORD),
                    headers={
                        "Content-Type": "application/x-protobuf",
                        "Content-Encoding": "snappy",
                        "X-Prometheus-Remote-Write-Version": settings.PROMETHEUS_REMOTE_WRITE_VERSION,
                    },
                    data=snappy.compress(request_data),
                )
                response.raise_for_status()
        except Exception as e:  # pylint: disable=W0718
            logger.exception("prometheus export failed: %s", e)

    @classmethod
    def current_ts(cls) -> int:
        return int(time.time() * 1000)

    @classmethod
    def hostname(cls) -> str:
        # pylint: disable=W0603
        global HOSTNAME, HOSTNAME_INIT

        if HOSTNAME_INIT:
            return HOSTNAME

        HOSTNAME = os.getenv("HOSTNAME")
        if HOSTNAME:
            HOSTNAME_INIT = True
            return HOSTNAME

        try:
            with open("/etc/hostname", "r", encoding="utf-8") as f:
                HOSTNAME = f.readline().strip()
        except Exception as e:  # pylint: disable=W0718
            logger.exception("prometheus export failed: %s", e)
        finally:
            HOSTNAME_INIT = True

        return HOSTNAME
