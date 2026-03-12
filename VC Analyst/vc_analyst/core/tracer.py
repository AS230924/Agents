"""
Phoenix by Arize observability setup.
Opt-in via PHOENIX_ENABLED=1 in .env.
UI available at http://localhost:6006 when running locally.
"""
from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)

_phoenix_session = None


def init_phoenix() -> None:
    """
    Start Phoenix server (local) and register OpenInference auto-instrumentation
    for OpenAI (Grok) and Anthropic SDK calls. No-op if PHOENIX_ENABLED != 1.
    """
    if not phoenix_enabled():
        return

    try:
        import phoenix as px
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        global _phoenix_session
        _phoenix_session = px.launch_app()          # starts http://localhost:6006
        endpoint = _phoenix_session.url + "/v1/traces"

        # Wire OTel → Phoenix OTLP exporter
        provider = TracerProvider()
        provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(provider)

        # Auto-instrument all OpenAI SDK calls (Grok uses OpenAI-compatible API)
        OpenAIInstrumentor().instrument()
        # Auto-instrument Anthropic SDK calls (fallback LLM)
        AnthropicInstrumentor().instrument()

        logger.info(f"Phoenix tracing enabled -> {_phoenix_session.url}")
        print(f"Phoenix UI: {_phoenix_session.url}")

    except ImportError:
        logger.warning(
            "Phoenix packages not installed — tracing disabled. "
            "To enable: pip install arize-phoenix openinference-instrumentation-openai "
            "openinference-instrumentation-anthropic opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-http"
        )
    except Exception as e:
        logger.warning(f"Phoenix init failed (continuing without tracing): {e}")


def phoenix_enabled() -> bool:
    """Return True if PHOENIX_ENABLED env var is set to a truthy value."""
    return os.getenv("PHOENIX_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def get_tracer():
    """
    Return an OpenTelemetry tracer for manual pipeline spans.
    When Phoenix is disabled, OTel uses a no-op provider — zero overhead.
    """
    from opentelemetry import trace
    return trace.get_tracer("vc_analyst")


def get_phoenix_url() -> str | None:
    """Return the local Phoenix UI URL if a session is active."""
    return _phoenix_session.url if _phoenix_session else None
