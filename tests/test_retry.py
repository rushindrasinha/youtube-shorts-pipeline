"""Tests for pipeline/retry.py — exponential backoff decorator."""

from unittest.mock import patch

import pytest

from pipeline.retry import with_retry


class TestWithRetry:
    def test_succeeds_first_try(self):
        @with_retry(max_retries=3, base_delay=0.01)
        def always_works():
            return "success"

        assert always_works() == "success"

    @patch("pipeline.retry.time.sleep")
    def test_retries_on_failure(self, mock_sleep):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("pipeline.retry.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        @with_retry(max_retries=2, base_delay=0.01)
        def always_fails():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            always_fails()
        # Should have slept twice (before retry 2 and 3)
        assert mock_sleep.call_count == 2

    @patch("pipeline.retry.time.sleep")
    def test_exponential_backoff(self, mock_sleep):
        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0)
        def fails_all():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fails_all()

        # Delays: 1.0, 2.0, 4.0
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert abs(delays[0] - 1.0) < 0.01
        assert abs(delays[1] - 2.0) < 0.01
        assert abs(delays[2] - 4.0) < 0.01

    def test_preserves_function_name(self):
        @with_retry(max_retries=1)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
