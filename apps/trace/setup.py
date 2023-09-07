from django.conf import settings
from django.utils.log import configure_logging
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from apps.trace.exporters import LazyBatchSpanProcessor
from apps.trace.instrumentors import Instrumentor
from apps.trace.utils import ServiceNameHandler, inject_logging_trace_info

# Adaptor for uwsgi postfork
try:
    from uwsgidecorators import postfork
except ImportError:
    from core.mock import PostFork as postfork


class TraceHandler:
    @staticmethod
    @postfork
    def setup():
        # use command below to start a local jaeger for trace log
        # docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one
        # use command below to change udp max dgram
        # sudo sysctl -w net.inet.udp.maxdgram=65535
        service_name = ServiceNameHandler(settings.SERVICE_NAME).get_service_name()
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: service_name, "token": settings.OTLP_TOKEN}),
                sampler=ALWAYS_ON,
            )
        )
        # otlp
        if settings.OTLP_HOST:
            exporter = OTLPSpanExporter(endpoint=settings.OTLP_HOST)
        # jaeger
        else:
            exporter = JaegerExporter(
                agent_host_name=settings.JAEGER_HOST, agent_port=settings.JAEGER_PORT, udp_split_oversized_batches=True
            )
        trace.get_tracer_provider().add_span_processor(LazyBatchSpanProcessor(exporter))
        Instrumentor().instrument()
        trace_format = (
            "[trace_id]: %(otelTraceID)s [span_id]: %(otelSpanID)s [resource.service.name]: %(otelServiceName)s"
        )
        inject_logging_trace_info(settings.LOGGING, ("verbose",), trace_format)
        configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
