from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings


def configure_tracing() -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME}))
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)))
    elif settings.DEBUG:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, attributes: dict[str, object] | None = None) -> Iterator[object]:
    tracer = trace.get_tracer(settings.OTEL_SERVICE_NAME)
    with tracer.start_as_current_span(name) as current:
        for key, value in (attributes or {}).items():
            current.set_attribute(key, value)
        yield current
