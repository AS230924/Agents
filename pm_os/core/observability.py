"""
Phoenix observability — auto-instrument OpenAI + Anthropic SDKs.

Launches Phoenix locally and attaches OpenTelemetry tracing so every
LLM call (Grok via OpenAI SDK, Haiku via Anthropic SDK) is captured
automatically — zero changes needed in llm_client.py or agent code.

Usage:
    from pm_os.core.observability import init_phoenix

    init_phoenix()  # call once at app startup

Set PHOENIX_ENABLED=0 to disable (e.g. in CI or lightweight test runs).
Phoenix UI runs at http://localhost:6006 by default.
"""

import logging
import os

log = logging.getLogger(__name__)

_initialized = False


def init_phoenix() -> bool:
    """
    Start Phoenix and instrument OpenAI + Anthropic SDKs.

    Returns True if Phoenix was successfully initialized, False otherwise.
    Safe to call multiple times — only initializes once.
    """
    global _initialized
    if _initialized:
        return True

    enabled = os.environ.get("PHOENIX_ENABLED", "1").lower() in ("1", "true", "yes")
    if not enabled:
        log.info("Phoenix disabled (PHOENIX_ENABLED=0)")
        return False

    try:
        import phoenix as px

        # Launch the Phoenix app (local server on port 6006)
        session = px.launch_app()
        phoenix_url = session.url if hasattr(session, "url") else "http://localhost:6006"
        log.info("Phoenix UI running at %s", phoenix_url)

        # Register OpenTelemetry tracer pointing to Phoenix
        from phoenix.otel import register

        tracer_provider = register(
            project_name=os.environ.get("PHOENIX_PROJECT_NAME", "pm-os"),
        )

        # Auto-instrument the OpenAI SDK (captures xAI Grok calls)
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            log.info("OpenAI SDK instrumented (captures Grok calls)")
        except Exception as e:
            log.warning("OpenAI instrumentation failed: %s", e)

        # Auto-instrument the Anthropic SDK (captures Haiku fallback calls)
        try:
            from openinference.instrumentation.anthropic import AnthropicInstrumentor

            AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
            log.info("Anthropic SDK instrumented (captures Haiku calls)")
        except Exception as e:
            log.warning("Anthropic instrumentation failed: %s", e)

        _initialized = True
        return True

    except ImportError as e:
        log.warning(
            "Phoenix not installed — run `pip install arize-phoenix "
            "openinference-instrumentation-openai "
            "openinference-instrumentation-anthropic` to enable. (%s)",
            e,
        )
        return False
    except Exception as e:
        log.warning("Phoenix initialization failed (non-fatal): %s", e)
        return False


def is_phoenix_enabled() -> bool:
    """Check if Phoenix was successfully initialized."""
    return _initialized
