"""Tests for lazy provider exports from mokli.providers."""

from __future__ import annotations

import importlib
import sys


def test_importing_providers_package_is_lazy(monkeypatch) -> None:
    original_package = sys.modules["mokli.providers"]
    monkeypatch.delitem(sys.modules, "mokli.providers", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.anthropic_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.openai_compat_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.openai_codex_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.xai_oauth", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.xai_grok_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.github_copilot_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.azure_openai_provider", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.bedrock_provider", raising=False)

    try:
        providers = importlib.import_module("mokli.providers")

        assert "mokli.providers.anthropic_provider" not in sys.modules
        assert "mokli.providers.openai_compat_provider" not in sys.modules
        assert "mokli.providers.openai_codex_provider" not in sys.modules
        assert "mokli.providers.xai_oauth" not in sys.modules
        assert "mokli.providers.xai_grok_provider" not in sys.modules
        assert "mokli.providers.github_copilot_provider" not in sys.modules
        assert "mokli.providers.azure_openai_provider" not in sys.modules
        assert "mokli.providers.bedrock_provider" not in sys.modules
        assert providers.__all__ == [
            "LLMProvider",
            "LLMResponse",
            "LLMUsage",
            "AnthropicProvider",
            "OpenAICompatProvider",
            "OpenAICodexProvider",
            "XAIGrokProvider",
            "GitHubCopilotProvider",
            "AzureOpenAIProvider",
            "BedrockProvider",
            "ClaudeCodeCliProvider",
        ]
    finally:
        # Importing a replacement subpackage also replaces mokli.providers on the
        # parent package. Restore both views so this isolation test cannot pollute
        # later tests that resolve a module through a dotted monkeypatch target.
        monkeypatch.undo()
        setattr(sys.modules["mokli"], "providers", original_package)


def test_explicit_provider_import_still_works(monkeypatch) -> None:
    original_package = sys.modules["mokli.providers"]
    monkeypatch.delitem(sys.modules, "mokli.providers", raising=False)
    monkeypatch.delitem(sys.modules, "mokli.providers.anthropic_provider", raising=False)

    try:
        namespace: dict[str, object] = {}
        exec("from mokli.providers import AnthropicProvider", namespace)

        assert namespace["AnthropicProvider"].__name__ == "AnthropicProvider"
        assert "mokli.providers.anthropic_provider" in sys.modules
    finally:
        monkeypatch.undo()
        setattr(sys.modules["mokli"], "providers", original_package)
