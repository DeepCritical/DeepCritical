"""Non-destructive GROBID-to-Docling scholarly annotation alignment."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any, cast

from defusedxml import ElementTree


class AlignmentStatus(StrEnum):
    ALIGNED = "aligned"
    UNALIGNED = "unaligned"


@dataclass(frozen=True, slots=True)
class GrobidCoordinate:
    page_number: int
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("GROBID coordinate page number must be positive")
        if not all(
            math.isfinite(value) for value in (self.x, self.y, self.width, self.height)
        ):
            raise ValueError("GROBID coordinates must be finite")
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError(
                "GROBID coordinates must have non-negative origins and positive size"
            )


@dataclass(frozen=True, slots=True)
class ScholarlyAnnotation:
    annotation_id: str
    kind: str
    text: str
    text_sha256: str
    tei_path: str
    xml_id: str | None
    target: str | None
    coordinates: tuple[GrobidCoordinate, ...]
    ref_type: str | None = None
    raw_coordinates: str | None = None
    coordinate_error: str | None = None


@dataclass(frozen=True, slots=True)
class AlignmentRecord:
    annotation: ScholarlyAnnotation
    status: AlignmentStatus
    docling_item_ref: str | None
    score: float
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ScholarlyAlignmentOverlay:
    records: tuple[AlignmentRecord, ...]
    aligned_count: int
    unaligned_count: int
    algorithm_version: str = "token-sequence-v2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_version": self.algorithm_version,
            "aligned_count": self.aligned_count,
            "unaligned_count": self.unaligned_count,
            "records": [asdict(record) for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ScholarlyAlignmentOverlay:
        """Validate and restore a persisted overlay without realigning evidence."""

        values = payload.get("records")
        if not isinstance(values, list):
            raise ValueError("scholarly alignment overlay records must be a list")
        records: list[AlignmentRecord] = []
        try:
            for value in values:
                if not isinstance(value, Mapping):
                    raise ValueError("alignment record must be an object")
                annotation_value = value.get("annotation")
                if not isinstance(annotation_value, Mapping):
                    raise ValueError("alignment annotation must be an object")
                coordinate_values = annotation_value.get("coordinates", [])
                if not isinstance(coordinate_values, (list, tuple)):
                    raise ValueError("annotation coordinates must be an array")
                coordinates = tuple(
                    GrobidCoordinate(
                        page_number=int(coordinate["page_number"]),
                        x=float(coordinate["x"]),
                        y=float(coordinate["y"]),
                        width=float(coordinate["width"]),
                        height=float(coordinate["height"]),
                    )
                    for coordinate in coordinate_values
                    if isinstance(coordinate, Mapping)
                )
                if len(coordinates) != len(coordinate_values):
                    raise ValueError("annotation coordinate must be an object")
                raw_coordinates = _optional_overlay_text(
                    annotation_value.get("raw_coordinates")
                )
                coordinate_error = _optional_overlay_text(
                    annotation_value.get("coordinate_error")
                )
                parsed_coordinates, parsed_coordinate_error = _parse_coordinates(
                    raw_coordinates
                )
                if (
                    coordinates != parsed_coordinates
                    or coordinate_error != parsed_coordinate_error
                ):
                    raise ValueError(
                        "annotation coordinates do not match their raw TEI evidence"
                    )
                annotation = ScholarlyAnnotation(
                    annotation_id=str(annotation_value["annotation_id"]),
                    kind=str(annotation_value["kind"]),
                    text=str(annotation_value["text"]),
                    text_sha256=str(annotation_value["text_sha256"]),
                    tei_path=str(annotation_value["tei_path"]),
                    xml_id=_optional_overlay_text(annotation_value.get("xml_id")),
                    target=_optional_overlay_text(annotation_value.get("target")),
                    coordinates=coordinates,
                    ref_type=_optional_overlay_text(annotation_value.get("ref_type")),
                    raw_coordinates=raw_coordinates,
                    coordinate_error=coordinate_error,
                )
                expected_text_hash = hashlib.sha256(
                    annotation.text.encode("utf-8")
                ).hexdigest()
                stable_source = _annotation_stable_source(annotation)
                expected_annotation_id = hashlib.sha256(
                    stable_source.encode("utf-8")
                ).hexdigest()
                if annotation.text_sha256 != expected_text_hash:
                    raise ValueError("annotation text hash does not match its text")
                if annotation.annotation_id != expected_annotation_id:
                    raise ValueError("annotation ID does not match its stable content")

                status = AlignmentStatus(str(value["status"]))
                item_ref = _optional_overlay_text(value.get("docling_item_ref"))
                if (status is AlignmentStatus.ALIGNED) != (item_ref is not None):
                    raise ValueError(
                        "alignment status and Docling item reference disagree"
                    )
                score = float(value["score"])
                if not 0 <= score <= 1:
                    raise ValueError("alignment score must be between zero and one")
                reason = _optional_overlay_text(value.get("reason"))
                if status is AlignmentStatus.ALIGNED and reason is not None:
                    raise ValueError("aligned records cannot have an unaligned reason")
                records.append(
                    AlignmentRecord(
                        annotation=annotation,
                        status=status,
                        docling_item_ref=item_ref,
                        score=score,
                        reason=reason,
                    )
                )
            aligned_count = int(payload["aligned_count"])
            unaligned_count = int(payload["unaligned_count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid scholarly alignment overlay") from exc

        actual_aligned = sum(
            record.status is AlignmentStatus.ALIGNED for record in records
        )
        if (
            aligned_count != actual_aligned
            or unaligned_count != len(records) - actual_aligned
        ):
            raise ValueError("scholarly alignment overlay counts do not match records")
        algorithm_version = str(payload.get("algorithm_version", "token-sequence-v2"))
        if not algorithm_version:
            raise ValueError("alignment algorithm version must not be empty")
        return cls(
            records=tuple(records),
            aligned_count=aligned_count,
            unaligned_count=unaligned_count,
            algorithm_version=algorithm_version,
        )


@dataclass(frozen=True, slots=True)
class _DoclingCandidate:
    item_ref: str
    text: str
    normalized: str
    tokens: frozenset[str]


class DoclingGrobidAligner:
    """Align GROBID TEI elements while preserving every unaligned annotation."""

    _TEI_KINDS = frozenset(
        {
            "title",
            "head",
            "p",
            "s",
            "ref",
            "biblStruct",
            "figure",
            "formula",
            "persName",
            "affiliation",
        }
    )
    _TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"

    def __init__(self, minimum_score: float = 0.72) -> None:
        if not 0 <= minimum_score <= 1:
            raise ValueError("minimum_score must be between 0 and 1")
        self.minimum_score = minimum_score

    def align(
        self, docling_document: dict[str, Any], grobid_tei: bytes
    ) -> ScholarlyAlignmentOverlay:
        candidates = _docling_candidates(docling_document)
        annotations = self.extract_annotations(grobid_tei)
        inverted_index = _build_inverted_index(candidates)
        records: list[AlignmentRecord] = []

        for annotation in annotations:
            if annotation.coordinate_error is not None:
                records.append(
                    AlignmentRecord(
                        annotation=annotation,
                        status=AlignmentStatus.UNALIGNED,
                        docling_item_ref=None,
                        score=0.0,
                        reason=f"invalid_grobid_coordinates:{annotation.coordinate_error}",
                    )
                )
                continue
            normalized = _normalize_text(annotation.text)
            annotation_tokens = frozenset(normalized.split())
            candidate_indexes: set[int] = set()
            for token in annotation_tokens:
                candidate_indexes.update(inverted_index.get(token, ()))
            if not candidate_indexes:
                candidate_indexes.update(range(len(candidates)))

            best_candidate: _DoclingCandidate | None = None
            best_score = 0.0
            for index in sorted(candidate_indexes):
                candidate = candidates[index]
                score = _alignment_score(
                    normalized,
                    annotation_tokens,
                    candidate.normalized,
                    candidate.tokens,
                )
                if score > best_score:
                    best_candidate = candidate
                    best_score = score

            aligned = best_candidate is not None and best_score >= self.minimum_score
            records.append(
                AlignmentRecord(
                    annotation=annotation,
                    status=(
                        AlignmentStatus.ALIGNED
                        if aligned
                        else AlignmentStatus.UNALIGNED
                    ),
                    docling_item_ref=(best_candidate.item_ref if aligned else None),
                    score=round(best_score, 6),
                    reason=None if aligned else "score_below_alignment_threshold",
                )
            )

        aligned_count = sum(
            record.status is AlignmentStatus.ALIGNED for record in records
        )
        return ScholarlyAlignmentOverlay(
            records=tuple(records),
            aligned_count=aligned_count,
            unaligned_count=len(records) - aligned_count,
        )

    def extract_annotations(self, grobid_tei: bytes) -> tuple[ScholarlyAnnotation, ...]:
        try:
            root = ElementTree.fromstring(grobid_tei)
        except ElementTree.ParseError as exc:
            raise ValueError("GROBID output is not valid TEI XML") from exc
        if root.tag != f"{{{self._TEI_NAMESPACE}}}TEI":
            raise ValueError(
                "GROBID output root must be TEI in the canonical TEI namespace"
            )
        annotations: list[ScholarlyAnnotation] = []
        self._walk_tei(root, f"/{_tei_path_segment(root.tag)}[1]", annotations)
        return tuple(annotations)

    def _walk_tei(
        self,
        element: Any,
        path: str,
        annotations: list[ScholarlyAnnotation],
    ) -> None:
        tag = _local_name(element.tag)
        if (
            _namespace_name(element.tag) == self._TEI_NAMESPACE
            and tag in self._TEI_KINDS
        ):
            text = " ".join("".join(element.itertext()).split())
            if text:
                xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
                target = element.attrib.get("target")
                raw_coordinates = element.attrib.get("coords")
                coordinates, coordinate_error = _parse_coordinates(raw_coordinates)
                ref_type = element.attrib.get("type")
                annotation_without_id = ScholarlyAnnotation(
                    annotation_id="pending",
                    kind=tag,
                    text=text,
                    text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    tei_path=path,
                    xml_id=xml_id,
                    target=target,
                    coordinates=coordinates,
                    ref_type=ref_type,
                    raw_coordinates=raw_coordinates,
                    coordinate_error=coordinate_error,
                )
                annotations.append(
                    ScholarlyAnnotation(
                        annotation_id=hashlib.sha256(
                            _annotation_stable_source(annotation_without_id).encode(
                                "utf-8"
                            )
                        ).hexdigest(),
                        kind=tag,
                        text=text,
                        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        tei_path=path,
                        xml_id=xml_id,
                        target=target,
                        coordinates=coordinates,
                        ref_type=ref_type,
                        raw_coordinates=raw_coordinates,
                        coordinate_error=coordinate_error,
                    )
                )

        child_counts: dict[str, int] = {}
        for child in list(element):
            child_tag = str(child.tag)
            child_counts[child_tag] = child_counts.get(child_tag, 0) + 1
            self._walk_tei(
                child,
                f"{path}/{_tei_path_segment(child_tag)}[{child_counts[child_tag]}]",
                annotations,
            )


def _docling_candidates(document: dict[str, Any]) -> tuple[_DoclingCandidate, ...]:
    candidates: list[_DoclingCandidate] = []
    for collection_name in ("texts", "tables", "pictures"):
        collection = document.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                continue
            item_dict = cast("dict[str, Any]", item)
            text = _docling_item_text(item_dict)
            normalized = _normalize_text(text)
            if not normalized:
                continue
            item_ref = item_dict.get("self_ref")
            if not isinstance(item_ref, str) or not item_ref:
                item_ref = f"#/{collection_name}/{index}"
            candidates.append(
                _DoclingCandidate(
                    item_ref=item_ref,
                    text=text,
                    normalized=normalized,
                    tokens=frozenset(normalized.split()),
                )
            )
    return tuple(candidates)


def _docling_item_text(item: dict[str, Any]) -> str:
    for key in ("text", "orig", "caption_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    data = item.get("data")
    if isinstance(data, dict):
        grid = data.get("grid") or data.get("table_cells")
        if isinstance(grid, list):
            values: list[str] = []
            for row in grid:
                if isinstance(row, list):
                    values.extend(str(cell) for cell in row if cell is not None)
                elif isinstance(row, dict):
                    text = row.get("text")
                    if text:
                        values.append(str(text))
            return " ".join(values)
    return ""


def _build_inverted_index(
    candidates: tuple[_DoclingCandidate, ...],
) -> dict[str, set[int]]:
    index: dict[str, set[int]] = {}
    for position, candidate in enumerate(candidates):
        for token in candidate.tokens:
            index.setdefault(token, set()).add(position)
    return index


def _alignment_score(
    left: str,
    left_tokens: frozenset[str],
    right: str,
    right_tokens: frozenset[str],
) -> float:
    if left == right:
        return 1.0
    if min(len(left), len(right)) >= 24 and (left in right or right in left):
        length_ratio = min(len(left), len(right)) / max(len(left), len(right))
        return 0.85 + 0.15 * length_ratio
    union = left_tokens | right_tokens
    token_score = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence_score = SequenceMatcher(None, left, right, autojunk=False).ratio()
    return 0.6 * sequence_score + 0.4 * token_score


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE))


def _optional_overlay_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("optional alignment text must be a non-empty string")
    return value


def _parse_coordinates(
    value: str | None,
) -> tuple[tuple[GrobidCoordinate, ...], str | None]:
    if value is None:
        return (), None
    if not value.strip():
        return (), "empty_coordinate_attribute"
    coordinates: list[GrobidCoordinate] = []
    for index, rectangle in enumerate(value.split(";"), start=1):
        parts = [part.strip() for part in rectangle.split(",")]
        if len(parts) != 5:
            return tuple(coordinates), f"rectangle_{index}_field_count"
        try:
            page, x, y, width, height = parts
            coordinates.append(
                GrobidCoordinate(
                    page_number=int(page),
                    x=float(x),
                    y=float(y),
                    width=float(width),
                    height=float(height),
                )
            )
        except (TypeError, ValueError):
            return tuple(coordinates), f"rectangle_{index}_invalid_values"
    return tuple(coordinates), None


def _annotation_stable_source(annotation: ScholarlyAnnotation) -> str:
    return "\x1f".join(
        (
            annotation.kind,
            annotation.xml_id or "",
            annotation.tei_path,
            annotation.text,
            annotation.target or "",
            annotation.ref_type or "",
            annotation.raw_coordinates or "",
            annotation.coordinate_error or "",
        )
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace_name(tag: str) -> str | None:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return None


def _tei_path_segment(tag: str) -> str:
    namespace = _namespace_name(tag)
    local_name = _local_name(tag)
    if namespace == DoclingGrobidAligner._TEI_NAMESPACE:
        return f"tei:{local_name}"
    if namespace is None:
        return f"no-namespace:{local_name}"
    return f"{{{namespace}}}{local_name}"


__all__ = [
    "AlignmentRecord",
    "AlignmentStatus",
    "DoclingGrobidAligner",
    "GrobidCoordinate",
    "ScholarlyAlignmentOverlay",
    "ScholarlyAnnotation",
]
