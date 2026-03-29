"""Observability module — structured logs, event bus, tracing, activity log, OpenTelemetry."""

from cognitia.observability.activity_log import ActivityLog, InMemoryActivityLog, SqliteActivityLog
from cognitia.observability.activity_subscriber import ActivityLogSubscriber
from cognitia.observability.activity_types import ActivityEntry, ActivityFilter, ActorType
from cognitia.observability.event_bus import EventBus, InMemoryEventBus
from cognitia.observability.logger import AgentLogger, configure_logging
from cognitia.observability.tracer import ConsoleTracer, NoopTracer, Tracer, TracingSubscriber

__all__ = [
    "ActivityEntry",
    "ActivityFilter",
    "ActivityLog",
    "ActivityLogSubscriber",
    "ActorType",
    "AgentLogger",
    "ConsoleTracer",
    "EventBus",
    "InMemoryActivityLog",
    "InMemoryEventBus",
    "NoopTracer",
    "OTelExporter",
    "SqliteActivityLog",
    "Tracer",
    "TracingSubscriber",
    "configure_logging",
]


def __getattr__(name: str) -> object:
    if name == "OTelExporter":
        from cognitia.observability.otel_exporter import OTelExporter

        return OTelExporter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
