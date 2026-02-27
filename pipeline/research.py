"""DuckDuckGo research — anti-hallucination gate."""

import requests
from html.parser import HTMLParser

from .config import extract_keywords
from .log import log
from .retry import with_retry


@with_retry(max_retries=2, base_delay=2.0)
def _fetch_ddg(keywords: str) -> str:
    """Fetch search snippets from DuckDuckGo HTML endpoint."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
    r = requests.post(url, data={"q": keywords}, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text


def research_topic(news: str) -> str:
    """DuckDuckGo search -> extract facts for anti-hallucination gate."""
    log("Researching topic via DuckDuckGo...")
    keywords = extract_keywords(news)

    try:
        html = _fetch_ddg(keywords)

        snippets = []

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self._in = False
                self._text = []

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                if tag == "a" and "result__snippet" in d.get("class", ""):
                    self._in = True
                    self._text = []

            def handle_endtag(self, tag):
                if self._in and tag == "a":
                    snippets.append("".join(self._text).strip())
                    self._in = False

            def handle_data(self, data):
                if self._in:
                    self._text.append(data)

        p = Parser()
        p.feed(html)
        # Sanitize snippets: truncate each to limit prompt injection surface
        snippets = [s[:300] for s in snippets]
        research = "\n".join(snippets[:8]) if snippets else ""
        if research:
            log(f"Found {len(snippets)} snippets.")
            return research
    except Exception as e:
        log(f"Research failed: {e} — proceeding without.")

    return f"Topic: {news}\n(No live research available — script must stay general.)"
