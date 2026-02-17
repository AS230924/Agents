"""
Multi-provider LLM client with automatic fallback.

Primary:  xAI Grok 4.1 Fast Reasoning  (via OpenAI-compatible API)
Fallback: Anthropic Claude Haiku 4.5

Set XAI_API_KEY for the primary provider.
Set ANTHROPIC_API_KEY (or OPENROUTER_API_KEY) for the fallback.

Phoenix auto-instruments both SDKs via OpenTelemetry. No manual tracing
code is needed here — just call init_phoenix() once at app startup.
"""

import logging
import os

log = logging.getLogger(__name__)

GROK_MODEL = "grok-4-1-fast-reasoning"
HAIKU_MODEL = "claude-haiku-4-5-20251001"


def _get_tracer():
    """Return an OTel tracer if Phoenix is active, else a no-op."""
    try:
        from opentelemetry import trace

        return trace.get_tracer("pm_os.llm_client")
    except ImportError:
        return None


def call_llm(
    *,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
    caller: str = "",
) -> str:
    """
    Call LLM with automatic provider fallback.

    Tries xAI Grok first, falls back to Anthropic Haiku on failure.

    Args:
        messages: list of {"role": ..., "content": ...} dicts
        system: optional system prompt (passed as top-level param for Anthropic,
                prepended as system message for xAI)
        max_tokens: max output tokens
        temperature: sampling temperature
        caller: optional label for tracing (e.g. "Framer", "intent_classifier")

    Returns:
        The model's text response.
    """
    tracer = _get_tracer()
    span_name = f"call_llm:{caller}" if caller else "call_llm"

    # If tracer is available, wrap the call in a span with metadata
    if tracer:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("pm_os.caller", caller or "unknown")
            span.set_attribute("pm_os.max_tokens", max_tokens)
            span.set_attribute("pm_os.temperature", temperature)
            return _call_with_fallback(messages, system, max_tokens, temperature, span)
    else:
        return _call_with_fallback(messages, system, max_tokens, temperature)


def _call_with_fallback(messages, system, max_tokens, temperature, span=None):
    """Execute the LLM call with xAI → Anthropic fallback."""
    xai_key = os.environ.get("XAI_API_KEY")
    if xai_key:
        try:
            if span:
                span.set_attribute("pm_os.provider", "xai")
                span.set_attribute("pm_os.model", GROK_MODEL)
            return _call_xai(xai_key, messages, system, max_tokens, temperature)
        except Exception as e:
            log.warning("Grok call failed, falling back to Haiku: %s", e)
            if span:
                span.set_attribute("pm_os.fallback", True)
                span.set_attribute("pm_os.provider", "anthropic")
                span.set_attribute("pm_os.model", HAIKU_MODEL)

    if span and not xai_key:
        span.set_attribute("pm_os.provider", "anthropic")
        span.set_attribute("pm_os.model", HAIKU_MODEL)

    return _call_anthropic(messages, system, max_tokens, temperature)


def _call_xai(api_key, messages, system, max_tokens, temperature):
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=GROK_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
    )
    return response.choices[0].message.content


def _call_anthropic(messages, system, max_tokens, temperature):
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    elif openrouter_key:
        client = anthropic.Anthropic(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        raise RuntimeError(
            "No LLM client available. "
            "Set XAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY."
        )

    kwargs = {
        "model": HAIKU_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text
