"""
Deep search data types for DeepCritical research workflows.

This module defines Pydantic models for deep search functionality including
web search, URL visiting, reflection, and answer generation operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvaluationType(str, Enum):
    """Types of evaluation for deep search results."""

    DEFINITIVE = "definitive"
    FRESHNESS = "freshness"
    PLURALITY = "plurality"
    ATTRIBUTION = "attribution"
    COMPLETENESS = "completeness"
    STRICT = "strict"


class ActionType(str, Enum):
    """Types of actions available to deep search agents."""

    SEARCH = "search"
    REFLECT = "reflect"
    VISIT = "visit"
    ANSWER = "answer"
    CODING = "coding"


class SearchTimeFilter:
    """Time filter for search operations."""

    PAST_HOUR = "qdr:h"
    PAST_DAY = "qdr:d"
    PAST_WEEK = "qdr:w"
    PAST_MONTH = "qdr:m"
    PAST_YEAR = "qdr:y"

    def __init__(self, filter_str: str):
        if filter_str not in [
            self.PAST_HOUR,
            self.PAST_DAY,
            self.PAST_WEEK,
            self.PAST_MONTH,
            self.PAST_YEAR,
        ]:
            msg = f"Invalid time filter: {filter_str}"
            raise ValueError(msg)
        self.value = filter_str

    def __str__(self) -> str:
        return self.value


# Constants for deep search operations
MAX_URLS_PER_STEP = 5
MAX_QUERIES_PER_STEP = 3
MAX_REFLECT_PER_STEP = 3


@dataclass
class SearchResult:
    """Individual search result."""

    title: str
    url: str
    snippet: str
    score: float = 0.0


@dataclass
class WebSearchRequest:
    """Web search request parameters."""

    query: str
    time_filter: SearchTimeFilter | None = None
    location: str | None = None
    max_results: int = 10


@dataclass
class URLVisitResult:
    """Result of visiting a URL."""

    url: str
    title: str
    content: str
    success: bool
    error: str | None = None
    processing_time: float = 0.0


@dataclass
class ReflectionQuestion:
    """Reflection question for deep search."""

    question: str
    priority: int = 1
    context: str | None = None


@dataclass
class PromptPair:
    """Pair of system and user prompts."""

    system: str
    user: str


class DeepSearchSchemas:
    """Python equivalent of the TypeScript Schemas class."""

    def __init__(self):
        self.language_style: str = "formal English"
        self.language_code: str = "en"
        self.search_language_code: str | None = None

        # Language mapping equivalent to TypeScript version
        self.language_iso6391_map = {
            "en": "English",
            "zh": "Chinese",
            "zh-CN": "Simplified Chinese",
            "zh-TW": "Traditional Chinese",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
            "hi": "Hindi",
            "bn": "Bengali",
            "tr": "Turkish",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "el": "Greek",
            "he": "Hebrew",
            "hu": "Hungarian",
            "id": "Indonesian",
            "ms": "Malay",
            "th": "Thai",
            "vi": "Vietnamese",
            "ro": "Romanian",
            "bg": "Bulgarian",
        }

    def get_language_prompt(self, question: str) -> PromptPair:
        """Get language detection prompt pair."""
        return PromptPair(
            system="""Identifies both the language used and the overall vibe of the question

<rules>
Combine both language and emotional vibe in a descriptive phrase, considering:
  - Language: The primary language or mix of languages used
  - Emotional tone: panic, excitement, frustration, curiosity, etc.
  - Formality level: academic, casual, professional, etc.
  - Domain context: technical, academic, social, etc.
</rules>

<examples>
Question: "fam PLEASE help me calculate the eigenvalues of this 4x4 matrix ASAP!! [matrix details] got an exam tmrw 😭"
Evaluation: {
    "langCode": "en",
    "langStyle": "panicked student English with math jargon"
}

Question: "Can someone explain how tf did Ferrari mess up their pit stop strategy AGAIN?! 🤦‍♂️ #MonacoGP"
Evaluation: {
    "langCode": "en",
    "languageStyle": "frustrated fan English with F1 terminology"
}

Question: "肖老师您好，请您介绍一下最近量子计算领域的三个重大突破，特别是它们在密码学领域的应用价值吗？🤔"
Evaluation: {
    "langCode": "zh",
    "languageStyle": "formal technical Chinese with academic undertones"
}

Question: "Bruder krass, kannst du mir erklären warum meine neural network training loss komplett durchdreht? Hab schon alles probiert 😤"
Evaluation: {
    "langCode": "de",
    "languageStyle": "frustrated German-English tech slang"
}

Question: "Does anyone have insights into the sociopolitical implications of GPT-4's emergence in the Global South, particularly regarding indigenous knowledge systems and linguistic diversity? Looking for a nuanced analysis."
Evaluation: {
    "langCode": "en",
    "languageStyle": "formal academic English with sociological terminology"
}

Question: "what's 7 * 9? need to check something real quick"
Evaluation: {
    "langCode": "en",
    "languageStyle": "casual English"
}
</examples>""",
            user=question,
        )

    async def set_language(self, query: str) -> None:
        """Set language based on query analysis."""
        if query in self.language_iso6391_map:
            self.language_code = query
