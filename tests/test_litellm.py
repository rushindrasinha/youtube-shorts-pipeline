"""Tests for LiteLLM provider integration in verticals/llm.py."""

import ast
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

LLM_PATH = Path(__file__).resolve().parents[1] / "verticals" / "llm.py"


class TestLiteLLMCodePath:
    """Verify the litellm branch exists in llm.py."""

    def test_litellm_branch_exists(self):
        src = LLM_PATH.read_text()
        assert 'provider == "litellm"' in src

    def test_call_litellm_function_exists(self):
        tree = ast.parse(LLM_PATH.read_text())
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "_call_litellm" in functions

    def test_uses_drop_params_true(self):
        src = LLM_PATH.read_text()
        assert "drop_params=True" in src

    def test_uses_litellm_completion(self):
        src = LLM_PATH.read_text()
        assert "litellm.completion(" in src

    def test_reads_litellm_model_from_env(self):
        src = LLM_PATH.read_text()
        assert "LITELLM_MODEL" in src

    def test_docstring_mentions_litellm(self):
        src = LLM_PATH.read_text()
        assert "litellm" in src.split('"""')[1].lower()


class TestLiteLLMCallFunction:
    """Test _call_litellm via the module import."""

    def test_call_litellm_returns_content(self):
        fake = types.ModuleType("litellm")
        mock_msg = MagicMock()
        mock_msg.content = "test response"
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        fake.completion = MagicMock(return_value=mock_resp)
        sys.modules["litellm"] = fake

        try:
            from verticals.llm import _call_litellm

            result = _call_litellm("hello", 100)
            assert result == "test response"
            kwargs = fake.completion.call_args.kwargs
            assert kwargs["drop_params"] is True
            assert kwargs["temperature"] == 0.7
        finally:
            del sys.modules["litellm"]

    def test_call_litellm_uses_env_model(self):
        fake = types.ModuleType("litellm")
        mock_msg = MagicMock(content="ok")
        mock_resp = MagicMock(choices=[MagicMock(message=mock_msg)])
        fake.completion = MagicMock(return_value=mock_resp)
        sys.modules["litellm"] = fake

        try:
            with patch.dict(
                os.environ, {"LITELLM_MODEL": "anthropic/claude-haiku-4-5"}
            ):
                from verticals.llm import _call_litellm

                _call_litellm("hi", 100)
                kwargs = fake.completion.call_args.kwargs
                assert kwargs["model"] == "anthropic/claude-haiku-4-5"
        finally:
            del sys.modules["litellm"]

    def test_call_litellm_raises_on_empty_response(self):
        fake = types.ModuleType("litellm")
        mock_msg = MagicMock(content="")
        mock_resp = MagicMock(choices=[MagicMock(message=mock_msg)])
        fake.completion = MagicMock(return_value=mock_resp)
        sys.modules["litellm"] = fake

        try:
            from verticals.llm import _call_litellm

            with pytest.raises(RuntimeError, match="Empty response"):
                _call_litellm("hi", 100)
        finally:
            del sys.modules["litellm"]

    def test_call_llm_routes_to_litellm(self):
        fake = types.ModuleType("litellm")
        mock_msg = MagicMock(content="routed ok")
        mock_resp = MagicMock(choices=[MagicMock(message=mock_msg)])
        fake.completion = MagicMock(return_value=mock_resp)
        sys.modules["litellm"] = fake

        try:
            from verticals.llm import call_llm

            result = call_llm("test prompt", provider="litellm")
            assert result == "routed ok"
        finally:
            del sys.modules["litellm"]


class TestRequirements:
    """Verify litellm is in requirements.txt."""

    def test_litellm_in_requirements(self):
        reqs = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text()
        assert "litellm" in reqs
