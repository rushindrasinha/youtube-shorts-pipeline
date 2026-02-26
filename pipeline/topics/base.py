"""TopicCandidate dataclass + TopicSource ABC."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TopicCandidate:
    """A discovered trending topic."""
    title: str
    source: str  # e.g. "reddit", "rss", "google_trends"
    trending_score: float = 0.0  # normalized 0-1
    summary: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)


class TopicSource(ABC):
    """Abstract base class for topic sources."""

    name: str = "unknown"

    @abstractmethod
    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        """Fetch trending topics from this source."""
        ...

    @property
    def is_available(self) -> bool:
        """Check if this source is configured and available."""
        return True
