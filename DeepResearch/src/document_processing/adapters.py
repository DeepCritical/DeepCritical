"""Format adapters that retain native JATS and BioC evidence locators.

These adapters do not attempt OCR, layout recovery, table recognition, or
scientific interpretation.  They only bridge established source formats into
Docling while keeping their native identifiers and offsets in an overlay.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from typing import Any

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .routing import InputFormat


class AdapterError(ValueError):
    """A structured source cannot be safely adapted."""


class AdapterDependencyError(AdapterError):
    """An optional, established format library is not installed."""


@dataclass(frozen=True, slots=True)
class NativeTextLocator:
    text: str
    source_kind: str
    document_index: int | None = None
    document_id: str | None = None
    passage_index: int | None = None
    sentence_index: int | None = None
    offset: int | None = None
    length: int | None = None
    xml_id: str | None = None
    xpath: str | None = None
    infons: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class AdaptedDocument:
    """A Docling-compatible projection plus a lossless native-locator overlay."""

    content: bytes
    filename: str
    media_type: str
    native_format: InputFormat
    locator_overlay: tuple[NativeTextLocator, ...]

    def overlay_json(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.locator_overlay]


class BioCAdapter:
    """Parse BioC with the maintained ``bioc`` package and project it to HTML."""

    def adapt(
        self,
        content: bytes,
        *,
        input_format: InputFormat,
        filename: str = "bioc-document.html",
    ) -> AdaptedDocument:
        if input_format not in {InputFormat.BIOC_JSON, InputFormat.BIOC_XML}:
            raise AdapterError(f"BioCAdapter cannot handle {input_format.value}")
        collection = self._load_collection(content, input_format)
        article_parts = ["<!doctype html><html><body>"]
        locators: list[NativeTextLocator] = []

        try:
            for document_index, document in enumerate(collection.documents):
                document_id = str(document.id) if document.id is not None else None
                article_parts.append(
                    f'<article data-bioc-document-id="{escape(document_id or "")}">'
                )
                for passage_index, passage in enumerate(document.passages):
                    passage_infons = _string_infons(passage.infons)
                    heading = passage_infons.get("section") or passage_infons.get(
                        "type"
                    )
                    if heading:
                        article_parts.append(f"<h2>{escape(heading)}</h2>")

                    passage_text = passage.text or ""
                    sentences = passage.sentences or ()
                    if passage_text:
                        passage_offset = int(passage.offset or 0)
                        sentence_projection = (
                            ' data-bioc-sentences="locator-overlay"'
                            if sentences
                            else ""
                        )
                        article_parts.append(
                            "<p "
                            f'data-bioc-passage="{passage_index}" '
                            f'data-bioc-offset="{passage_offset}"'
                            f"{sentence_projection}>"
                            f"{escape(passage_text)}</p>"
                        )
                        locators.append(
                            NativeTextLocator(
                                text=passage_text,
                                source_kind=input_format.value,
                                document_index=document_index,
                                document_id=document_id,
                                passage_index=passage_index,
                                offset=passage_offset,
                                length=len(passage_text),
                                infons=passage_infons,
                            )
                        )

                    for sentence_index, sentence in enumerate(sentences):
                        sentence_text = sentence.text or ""
                        sentence_offset = int(sentence.offset or 0)
                        # BioC permits a passage to retain both its complete text
                        # and sentence-level annotations.  In that case, render
                        # only the passage text for Docling's content order and
                        # retain sentences in the native-locator overlay.  A
                        # sentence-only passage still needs an HTML projection.
                        if not passage_text and sentence_text:
                            article_parts.append(
                                "<p "
                                f'data-bioc-passage="{passage_index}" '
                                f'data-bioc-sentence="{sentence_index}" '
                                f'data-bioc-offset="{sentence_offset}">'
                                f"{escape(sentence_text)}</p>"
                            )
                        locators.append(
                            NativeTextLocator(
                                text=sentence_text,
                                source_kind=input_format.value,
                                document_index=document_index,
                                document_id=document_id,
                                passage_index=passage_index,
                                sentence_index=sentence_index,
                                offset=sentence_offset,
                                length=len(sentence_text),
                                infons=_string_infons(sentence.infons),
                            )
                        )
                article_parts.append("</article>")
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise AdapterError(
                f"Invalid {input_format.value} document structure"
            ) from exc
        article_parts.append("</body></html>")

        return AdaptedDocument(
            content="".join(article_parts).encode("utf-8"),
            filename=filename,
            media_type="text/html",
            native_format=input_format,
            locator_overlay=tuple(locators),
        )

    @staticmethod
    def _load_collection(content: bytes, input_format: InputFormat) -> Any:
        try:
            from bioc import biocjson, biocxml
        except ImportError as exc:
            raise AdapterDependencyError(
                "BioC input requires the 'bioc' document-processing dependency"
            ) from exc

        try:
            decoded = content.decode("utf-8-sig")
            if input_format is InputFormat.BIOC_JSON:
                return biocjson.loads(decoded)
            root = ElementTree.fromstring(
                content,
                forbid_dtd=True,
                forbid_entities=True,
                forbid_external=True,
            )
            if _local_name(root.tag) != "collection":
                raise AdapterError("BioC XML root element must be <collection>")
            return biocxml.loads(decoded)
        except AdapterError:
            raise
        except ImportError as exc:
            raise AdapterDependencyError(
                "BioC input requires its XML/JSON parser dependencies"
            ) from exc
        except (
            AttributeError,
            DefusedXmlException,
            ElementTree.ParseError,
            IndexError,
            KeyError,
            OSError,
            OverflowError,
            RecursionError,
            SyntaxError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            raise AdapterError(f"Invalid {input_format.value} document") from exc


def _string_infons(infons: Any) -> dict[str, str]:
    return {str(key): str(value) for key, value in (infons or {}).items()}


class JATSLocatorAdapter:
    """Extract native IDs/XPaths without replacing the authoritative JATS XML."""

    _TEXT_TAGS = frozenset(
        {
            "article-title",
            "title",
            "subtitle",
            "p",
            "label",
            "caption",
            "td",
            "th",
            "mixed-citation",
            "element-citation",
        }
    )

    def extract_locators(self, content: bytes) -> tuple[NativeTextLocator, ...]:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise AdapterError("Invalid JATS XML") from exc
        if _local_name(root.tag) != "article":
            raise AdapterError("JATS root element must be <article>")

        locators: list[NativeTextLocator] = []
        self._walk(root, f"/{_xpath_segment(root.tag, 1)}", locators)
        return tuple(locators)

    def _walk(
        self,
        element: Any,
        xpath: str,
        locators: list[NativeTextLocator],
    ) -> None:
        tag = _local_name(element.tag)
        if tag in self._TEXT_TAGS:
            text = " ".join("".join(element.itertext()).split())
            if text:
                locators.append(
                    NativeTextLocator(
                        text=text,
                        source_kind=InputFormat.JATS.value,
                        xml_id=element.attrib.get(
                            "{http://www.w3.org/XML/1998/namespace}id"
                        )
                        or element.attrib.get("id"),
                        xpath=xpath,
                    )
                )

        counts: dict[str, int] = {}
        for child in list(element):
            child_tag = str(child.tag)
            counts[child_tag] = counts.get(child_tag, 0) + 1
            self._walk(
                child,
                f"{xpath}/{_xpath_segment(child.tag, counts[child_tag])}",
                locators,
            )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xpath_segment(tag: str, index: int) -> str:
    """Build a self-contained XPath 1.0 name test, including namespaces."""

    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", 1)
        return (
            "*[local-name()="
            f"{_xpath_literal(local_name)} and namespace-uri()="
            f"{_xpath_literal(namespace)}][{index}]"
        )
    return f"{tag}[{index}]"


def _xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\'", '.join(f"'{part}'" for part in parts) + ")"


__all__ = [
    "AdaptedDocument",
    "AdapterDependencyError",
    "AdapterError",
    "BioCAdapter",
    "JATSLocatorAdapter",
    "NativeTextLocator",
]
