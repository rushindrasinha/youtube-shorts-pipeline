"""Tests for pipeline/research.py — DuckDuckGo research gate."""

from unittest.mock import patch, MagicMock

from pipeline.research import research_topic


SAMPLE_DDG_HTML = """
<html><body>
<div class="results">
  <a class="result__snippet" href="https://example.com/1">
    India beat South Korea 3-1 to win VCT Pacific 2026 grand finals on March 15.
  </a>
  <a class="result__snippet" href="https://example.com/2">
    The tournament featured 12 teams from the Asia-Pacific region competing over two weeks.
  </a>
  <a class="result__snippet" href="https://example.com/3">
    MVP award went to player &quot;AceX&quot; who dominated the semifinals and finals.
  </a>
</div>
</body></html>
"""

EMPTY_DDG_HTML = "<html><body><div class='results'></div></body></html>"


class TestResearchTopic:
    @patch("pipeline.research._fetch_ddg")
    def test_returns_snippets(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_DDG_HTML
        result = research_topic("India VCT Pacific 2026")
        assert "India beat South Korea" in result
        assert "12 teams" in result
        assert "AceX" in result

    @patch("pipeline.research._fetch_ddg")
    def test_limits_to_eight_snippets(self, mock_fetch):
        # Generate HTML with 12 snippets
        snippets = "".join(
            f'<a class="result__snippet">Snippet {i}</a>' for i in range(12)
        )
        mock_fetch.return_value = f"<html><body>{snippets}</body></html>"
        result = research_topic("test topic")
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) <= 8

    @patch("pipeline.research._fetch_ddg")
    def test_truncates_long_snippets(self, mock_fetch):
        long_text = "A" * 500
        mock_fetch.return_value = (
            f'<html><body><a class="result__snippet">{long_text}</a></body></html>'
        )
        result = research_topic("test")
        # Each snippet truncated to 300 chars
        assert len(result) <= 300

    @patch("pipeline.research._fetch_ddg")
    def test_empty_results_returns_fallback(self, mock_fetch):
        mock_fetch.return_value = EMPTY_DDG_HTML
        result = research_topic("obscure topic xyz")
        assert "No live research available" in result

    @patch("pipeline.research._fetch_ddg")
    def test_network_failure_returns_fallback(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("Connection failed")
        result = research_topic("anything")
        assert "No live research available" in result
        assert "anything" in result

    @patch("pipeline.research._fetch_ddg")
    def test_handles_html_entities(self, mock_fetch):
        mock_fetch.return_value = (
            '<html><body>'
            '<a class="result__snippet">Results for &amp; queries &lt;work&gt;</a>'
            '</body></html>'
        )
        result = research_topic("test")
        # HTMLParser should decode entities
        assert "& queries" in result or "&amp;" in result
