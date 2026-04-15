"""FallbackChain — try a sequence of providers and return the first success."""

from __future__ import annotations

from .log import log


class FallbackChain:
    """Ordered chain of callables; returns the first successful result.

    Usage::

        result = (
            FallbackChain("voiceover")
            .add("kokoro", lambda: _generate_kokoro(...))
            .add("edge_tts", lambda: _generate_edge_tts(...))
            .add("say", lambda: _generate_say(...))
            .execute()
        )
    """

    def __init__(self, name: str):
        self._name = name
        self._providers: list[tuple[str, object, object]] = []

    def add(self, name: str, fn, condition=None) -> "FallbackChain":
        """Register a provider.

        Args:
            name: Human-readable label used in log messages.
            fn: Zero-argument callable that performs the work.
            condition: Optional zero-argument callable; when provided the
                       provider is skipped if it returns falsy.

        Returns:
            self, for chaining.
        """
        self._providers.append((name, fn, condition))
        return self

    def execute(self):
        """Try each provider in order; return first success.

        Raises:
            RuntimeError: If all providers fail.
        """
        errors: list[str] = []

        for provider_name, fn, condition in self._providers:
            if condition is not None and not condition():
                log(f"[{self._name}] Skipping {provider_name} (condition not met)")
                continue
            try:
                result = fn()
                log(f"[{self._name}] {provider_name} succeeded")
                return result
            except Exception as exc:
                log(f"[{self._name}] {provider_name} failed: {exc}")
                errors.append(f"{provider_name}: {exc}")

        raise RuntimeError(
            f"[{self._name}] All providers failed:\n" + "\n".join(errors)
        )
