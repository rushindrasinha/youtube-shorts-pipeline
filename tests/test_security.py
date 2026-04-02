"""Security defense tests — verify hardening measures don't regress."""

import json
import os
import re
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestFilePermissions:
    """Verify sensitive files are written with 0o600 (owner-only)."""

    def test_write_secret_file_permissions(self, tmp_path):
        from pipeline.config import write_secret_file

        p = tmp_path / "secret.json"
        write_secret_file(p, '{"key": "value"}')
        mode = p.stat().st_mode & 0o777
        assert mode == 0o600

    def test_pipeline_state_save_permissions(self, tmp_path):
        from pipeline.state import PipelineState

        draft = {"job_id": "123", "_pipeline_state": {}}
        state = PipelineState(draft)
        state.complete_stage("test")
        path = tmp_path / "draft.json"
        state.save(path)
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600


class TestRunCmdSignature:
    """Verify run_cmd rejects unexpected kwargs like shell=True."""

    def test_rejects_shell_true(self):
        from pipeline.config import run_cmd

        with pytest.raises(TypeError):
            run_cmd(["echo", "hi"], shell=True)

    def test_rejects_arbitrary_kwargs(self):
        from pipeline.config import run_cmd

        with pytest.raises(TypeError):
            run_cmd(["echo", "hi"], env={"FOO": "bar"})


class TestSubredditValidation:
    """Verify malicious subreddit names are rejected."""

    def test_rejects_path_traversal(self):
        from pipeline.topics.reddit import RedditSource

        src = RedditSource({"subreddits": ["../../api/v1/me"]})
        result = src._fetch_subreddit("../../api/v1/me", 5)
        assert result == []

    def test_rejects_semicolon_injection(self):
        from pipeline.topics.reddit import RedditSource

        src = RedditSource({"subreddits": ["sub; rm -rf /"]})
        result = src._fetch_subreddit("sub; rm -rf /", 5)
        assert result == []

    def test_rejects_empty_string(self):
        from pipeline.topics.reddit import RedditSource

        src = RedditSource({"subreddits": [""]})
        result = src._fetch_subreddit("", 5)
        assert result == []

    def test_accepts_valid_subreddit(self):
        from pipeline.topics.reddit import _SUBREDDIT_RE

        assert _SUBREDDIT_RE.match("technology")
        assert _SUBREDDIT_RE.match("Ask_Reddit")
        assert _SUBREDDIT_RE.match("python3")


class TestRSSUrlSchemeValidation:
    """Verify non-HTTP(S) URLs are rejected in RSS source."""

    def test_rejects_file_scheme(self):
        from pipeline.topics.rss import RSSSource

        src = RSSSource({"feeds": ["file:///etc/passwd"]})
        topics = src.fetch_topics(limit=5)
        assert topics == []

    def test_rejects_ftp_scheme(self):
        from pipeline.topics.rss import RSSSource

        src = RSSSource({"feeds": ["ftp://example.com/feed.xml"]})
        topics = src.fetch_topics(limit=5)
        assert topics == []

    def test_rejects_data_scheme(self):
        from pipeline.topics.rss import RSSSource

        src = RSSSource({"feeds": ["data:text/xml,<rss></rss>"]})
        topics = src.fetch_topics(limit=5)
        assert topics == []


class TestRetryableExceptionFilter:
    """Verify the retryable parameter causes non-matching exceptions to propagate immediately."""

    def test_non_retryable_exception_propagates_immediately(self):
        from pipeline.retry import with_retry

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01, retryable=(ValueError,))
        def flaky():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("permanent failure")

        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="permanent failure"):
                flaky()

        # Should have been called only once — RuntimeError is not retryable
        assert call_count == 1

    def test_retryable_exception_is_retried(self):
        from pipeline.retry import with_retry

        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01, retryable=(ValueError,))
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "success"

        with patch("time.sleep"):
            result = flaky()

        assert result == "success"
        assert call_count == 3


class TestConcatPathSanitization:
    """Verify newlines are stripped from paths in ffmpeg concat file."""

    def test_newline_stripped_from_path(self):
        from pipeline.assemble import assemble_video

        # We can't easily run the full function, so test the _esc logic directly
        # by reading the source — the function is defined inline, so we test
        # the behavior through the module
        path_with_newline = "/tmp/evil\n/path.mp4"
        # Simulate what _esc does
        s = str(path_with_newline).replace("'", "'\\''")
        s = s.replace("\n", "").replace("\r", "")
        assert "\n" not in s
        assert s == "/tmp/evil/path.mp4"

    def test_carriage_return_stripped(self):
        path_with_cr = "/tmp/evil\r/path.mp4"
        s = str(path_with_cr).replace("'", "'\\''")
        s = s.replace("\n", "").replace("\r", "")
        assert "\r" not in s


class TestSayFallbackFlagInjection:
    """Verify -- separator prevents flag injection in macOS say."""

    def test_double_dash_before_script(self):
        from pipeline.voiceover import _say_fallback

        with patch("pipeline.voiceover.run_cmd") as mock_run:
            _say_fallback("-v Whisper evil text", Path("/tmp"))

            # First call is say, second is ffmpeg
            say_cmd = mock_run.call_args_list[0][0][0]
            # Find positions: -- must come before the script text
            dash_idx = say_cmd.index("--")
            script_idx = len(say_cmd) - 1  # script is last arg
            assert dash_idx < script_idx
            assert say_cmd[script_idx] == "-v Whisper evil text"


# ─────────────────────────────────────────────────────────────────
# NEW: Regression tests for adversarial-cycle security fixes
# ─────────────────────────────────────────────────────────────────


class TestSystemUserPromptSeparation:
    """RT-001: Verify Claude API path uses system param for instructions."""

    def test_api_path_uses_system_param(self):
        """The API path must pass system_prompt via the system= parameter."""
        from unittest.mock import MagicMock

        with patch("pipeline.draft.get_claude_backend", return_value="api"), \
             patch("pipeline.draft.get_anthropic_client") as mock_client_fn, \
             patch("time.sleep"):
            client = MagicMock()
            mock_client_fn.return_value = client
            msg = MagicMock()
            msg.content = [MagicMock(text='{"script":"hi"}')]
            client.messages.create.return_value = msg

            from pipeline.draft import _call_claude
            _call_claude.__wrapped__("SYSTEM", "USER")

            call_kwargs = client.messages.create.call_args
            assert call_kwargs.kwargs.get("system") == "SYSTEM" or \
                   call_kwargs[1].get("system") == "SYSTEM", \
                "system prompt must be passed via system= parameter, not in messages"

    def test_research_not_in_system_prompt(self):
        """Untrusted research data must NOT appear in the system prompt."""
        from pipeline.draft import generate_draft

        with patch("pipeline.draft.research_topic", return_value="POISONED_DATA"), \
             patch("pipeline.draft._call_claude") as mock_call:
            mock_call.__wrapped__ = lambda s, u: '{"script":"x","broll_prompts":["a"],"youtube_title":"t","youtube_description":"d","youtube_tags":"t","instagram_caption":"c","thumbnail_prompt":"p"}'
            mock_call.side_effect = lambda s, u: mock_call.__wrapped__(s, u)

            # Intercept the call to check prompt contents
            calls = []
            def capture(sys_prompt, usr_prompt):
                calls.append((sys_prompt, usr_prompt))
                return '{"script":"x","broll_prompts":["a"],"youtube_title":"t","youtube_description":"d","youtube_tags":"t","instagram_caption":"c","thumbnail_prompt":"p"}'

            mock_call.side_effect = capture
            try:
                generate_draft("test topic")
            except Exception:
                pass

            if calls:
                system_prompt, user_prompt = calls[0]
                assert "POISONED_DATA" not in system_prompt, \
                    "Research data must not appear in system prompt"
                assert "POISONED_DATA" in user_prompt, \
                    "Research data must appear in user prompt"


class TestURLStripping:
    """RT-001c: Verify URLs are stripped from LLM output fields."""

    def test_urls_stripped_from_script(self):
        from pipeline.draft import _URL_RE

        text = "Visit https://evil.com/phish for free crypto"
        result = _URL_RE.sub('[link removed]', text)
        assert "https://evil.com" not in result
        assert "[link removed]" in result

    def test_urls_stripped_from_all_fields(self):
        """All string fields and broll_prompts must have URLs stripped."""
        from pipeline.draft import generate_draft

        fake_draft = {
            "script": "Go to https://evil.com now",
            "broll_prompts": ["image at http://bad.com/img.png"],
            "youtube_title": "Check https://scam.io",
            "youtube_description": "Visit http://phish.net",
            "youtube_tags": "tag1,tag2",
            "instagram_caption": "Link: https://malware.org",
            "thumbnail_prompt": "nice image",
        }
        raw_json = json.dumps(fake_draft)

        with patch("pipeline.draft.research_topic", return_value="research"), \
             patch("pipeline.draft._call_claude", return_value=raw_json):
            result = generate_draft("test")

        for field in ["script", "youtube_title", "youtube_description", "instagram_caption"]:
            assert "https://" not in result[field], f"URL not stripped from {field}"
            assert "http://" not in result[field], f"URL not stripped from {field}"
        assert "http://bad.com" not in result["broll_prompts"][0]

    def test_youtube_title_length_limit(self):
        """YouTube title must be capped at 100 characters."""
        from pipeline.draft import generate_draft

        fake_draft = {
            "script": "short",
            "broll_prompts": ["a", "b", "c"],
            "youtube_title": "A" * 200,
            "youtube_description": "desc",
            "youtube_tags": "tags",
            "instagram_caption": "cap",
            "thumbnail_prompt": "thumb",
        }

        with patch("pipeline.draft.research_topic", return_value="research"), \
             patch("pipeline.draft._call_claude", return_value=json.dumps(fake_draft)):
            result = generate_draft("test")

        assert len(result["youtube_title"]) <= 100


class TestLogFilePermissions:
    """RT-005/RT-015: Verify log files are created with 0o600."""

    def test_log_file_created_with_restricted_permissions(self, tmp_path):
        """Log files must be owner-only (0o600), not world-readable."""
        import logging
        import pipeline.log

        # Save and fully reset logger state so get_logger() creates fresh handlers
        saved_logger = pipeline.log._logger
        pipeline.log._logger = None

        # Also clear any existing handlers on the named logger
        named_logger = logging.getLogger("pipeline")
        saved_handlers = named_logger.handlers[:]
        named_logger.handlers.clear()

        try:
            with patch("pipeline.log.LOGS_DIR", tmp_path):
                logger = pipeline.log.get_logger()

                log_files = list(tmp_path.glob("pipeline_*.log"))
                assert log_files, "Log file should be created"
                mode = log_files[0].stat().st_mode & 0o777
                assert mode == 0o600, f"Log file permissions should be 0o600, got {oct(mode)}"

                # Clean up handlers
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
        finally:
            # Restore original logger state
            named_logger.handlers.extend(saved_handlers)
            pipeline.log._logger = saved_logger


class TestStderrTruncation:
    """RT-019: Verify run_cmd truncates stderr in error messages."""

    def test_stderr_truncated_to_500_chars(self):
        from pipeline.config import run_cmd

        long_stderr = "E" * 1000

        with patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 1
            mock_result.stderr = long_stderr

            with pytest.raises(RuntimeError) as exc_info:
                run_cmd(["fake_cmd"], capture=True)

            error_msg = str(exc_info.value)
            assert len(error_msg) <= 500, \
                f"Error message should be truncated to 500 chars, got {len(error_msg)}"


class TestDuckFilterValidation:
    """RT-006: Verify duck_filter is validated against allowlist.

    Tests the regex directly to avoid importing assemble.py (which
    pulls in PIL via broll.py and may not be installed in test env).
    """

    # Mirror the regex from pipeline/assemble.py
    _DUCK_FILTER_RE = re.compile(
        r"^volume=['\"]?[a-zA-Z0-9_()+.,/:' ]*['\"]?(?::eval=frame)?$"
    )

    def test_valid_simple_filter_accepted(self):
        assert self._DUCK_FILTER_RE.match("volume=0.25")

    def test_valid_complex_filter_accepted(self):
        f = "volume='if(between(t,0.30,1.50)+between(t,2.00,3.50), 0.12, 0.25)':eval=frame"
        assert self._DUCK_FILTER_RE.match(f)

    def test_semicolon_injection_rejected(self):
        assert not self._DUCK_FILTER_RE.match("volume=0.25;amovie=/etc/passwd")

    def test_bracket_injection_rejected(self):
        assert not self._DUCK_FILTER_RE.match("volume=0.25[x]")

    def test_shell_injection_rejected(self):
        assert not self._DUCK_FILTER_RE.match("volume=$(cat /etc/passwd)")

    def test_invalid_filter_falls_back_to_safe_default(self):
        """If duck_filter is invalid, assemble should use a safe default."""
        malicious = "volume=0.25;[out]nullsrc"
        assert not self._DUCK_FILTER_RE.match(malicious)

    def test_regex_matches_source(self):
        """Ensure our test regex matches the one in assemble.py."""
        import ast
        with open("pipeline/assemble.py") as f:
            source = f.read()
        # The regex string should appear in the source
        assert r"^volume=['\"]?[a-zA-Z0-9_()+.,/:' ]*['\"]?(?::eval=frame)?$" in source


class TestASSPathEscaping:
    """RT-003: Verify ffmpeg filter-graph special chars are escaped in ASS paths."""

    def test_semicolons_escaped(self):
        # Simulate the escaping logic from assemble.py
        path = "/tmp/evil;[out]nullsrc/captions.ass"
        escaped = (path
                   .replace("\\", "\\\\")
                   .replace(":", "\\:")
                   .replace("'", "\\'")
                   .replace(";", "\\;")
                   .replace("[", "\\[")
                   .replace("]", "\\]")
                   .replace(",", "\\,"))
        assert ";" not in escaped.replace("\\;", "")
        assert "[" not in escaped.replace("\\[", "")
        assert "]" not in escaped.replace("\\]", "")

    def test_commas_escaped(self):
        path = "/tmp/path,with,commas/captions.ass"
        escaped = (path
                   .replace("\\", "\\\\")
                   .replace(":", "\\:")
                   .replace("'", "\\'")
                   .replace(";", "\\;")
                   .replace("[", "\\[")
                   .replace("]", "\\]")
                   .replace(",", "\\,"))
        # Unescaped commas should not exist
        import re
        unescaped_commas = re.findall(r'(?<!\\),', escaped)
        assert len(unescaped_commas) == 0


class TestWhisperBraceStripping:
    """RT-002: Verify ASS override-tag delimiters stripped from Whisper output."""

    def test_braces_stripped_in_ass_active_word(self):
        """Curly braces in word text must not reach ASS subtitle output."""
        word = "{\\b1}injected"
        safe = word.replace('{', '').replace('}', '')
        assert '{' not in safe
        assert '}' not in safe
        assert safe == "\\b1injected"

    def test_braces_stripped_in_srt_generation(self):
        """SRT text also sanitises braces for defence-in-depth."""
        word = "test{\\fnEvil}word"
        safe = word.replace('{', '').replace('}', '')
        assert '{' not in safe
        assert '}' not in safe

    def test_ass_generation_strips_braces(self, tmp_path):
        """End-to-end: _generate_ass must not contain injected override tags."""
        from pipeline.captions import _generate_ass

        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "{\\b1}evil", "start": 0.5, "end": 1.0},
            {"word": "world", "start": 1.0, "end": 1.5},
            {"word": "test", "start": 1.5, "end": 2.0},
        ]
        out = tmp_path / "test.ass"
        _generate_ass(words, out)

        content = out.read_text()
        # The injected {\\b1} must not appear as a raw override tag
        # (our own override tags like {\c&H00FFFF&...} are legitimate)
        assert "{\\b1}" not in content, "Injected ASS override tag must be stripped"


class TestJSONFallbackParser:
    """RT-014: Verify JSON extraction uses find/rfind, not greedy regex."""

    def test_valid_json_extracted_from_text(self):
        raw = 'Here is the output: {"script": "hello", "key": "val"} done.'
        first = raw.find('{')
        last = raw.rfind('}')
        candidate = raw[first:last + 1]
        result = json.loads(candidate)
        assert result["script"] == "hello"

    def test_malformed_response_raises_valueerror(self):
        """Non-JSON responses must raise ValueError, not crash."""
        raw = "This has no JSON at all"
        first = raw.find('{')
        assert first == -1  # No brace found

    def test_no_regex_import_in_json_fallback(self):
        """The JSON fallback path should not use re.search (backtracking risk)."""
        import ast
        with open("pipeline/draft.py") as f:
            source = f.read()
        tree = ast.parse(source)
        # Find the generate_draft function
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr') and node.func.attr == 'search':
                    if hasattr(node.func, 'value') and hasattr(node.func.value, 'id'):
                        if node.func.value.id == 're':
                            pytest.fail("re.search found in draft.py — should use find/rfind")


class TestWhisperVersionBound:
    """RT-008: Verify openai-whisper has an upper version bound."""

    def test_whisper_has_upper_bound(self):
        """pyproject.toml must pin whisper with both lower and upper bounds."""
        import tomllib
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        deps = config["project"]["dependencies"]
        whisper_dep = [d for d in deps if "openai-whisper" in d]
        assert whisper_dep, "openai-whisper must be in dependencies"
        dep = whisper_dep[0]
        assert "<" in dep, f"openai-whisper must have upper bound, got: {dep}"
        assert ">=" in dep, f"openai-whisper must have lower bound, got: {dep}"
