"""
Markdown code extractor for DeepCritical.

Adapted from AG2 for extracting code blocks from markdown-formatted text.
"""

from DeepResearch.src.datatypes.ag_types import (
    UserMessageImageContentPart,
    UserMessageTextContentPart,
    content_str,
)
from DeepResearch.src.utils.code_utils import CODE_BLOCK_PATTERN, UNKNOWN, extract_code

from .base import CodeBlock, CodeExtractor


class MarkdownCodeExtractor(CodeExtractor):
    """A code extractor class that extracts code blocks from markdown text."""

    def __init__(self, language: str | None = None):
        """Initialize the markdown code extractor.

        Args:
            language: The default language to use if not specified in code blocks.
        """
        self.language = language

    def extract_code_blocks(
        self,
        message: str
        | list[UserMessageTextContentPart | UserMessageImageContentPart]
        | None,
    ) -> list[CodeBlock]:
        """Extract code blocks from a message.

        Args:
            message: The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks.
        """
        text = content_str(message)
        code_blocks = extract_code(text, CODE_BLOCK_PATTERN)

        result = []
        for lang, code in code_blocks:
            if lang == UNKNOWN:
                # No code blocks found, treat the entire text as code
                if self.language:
                    result.append(CodeBlock(code=text, language=self.language))
                continue

            # Use specified language or default
            block_lang = lang if lang else self.language or "python"
            result.append(CodeBlock(code=code, language=block_lang))

        return result
