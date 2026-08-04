"""Registry and constructors for typed document-processing data products."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .models import DataProductRef, configuration_sha256


@dataclass(frozen=True, slots=True)
class ProductDefinition:
    """Declared media and payload schema for one logical product name."""

    media_type: str
    payload_schema_uri: str
    payload_schema_version: str


_JSON = "application/json"
_PRODUCT_DEFINITIONS = {
    "preflight_result": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:preflight-result",
        "deepcritical-preflight-result-v1",
    ),
    "native_locator_overlay": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:native-locator-overlay",
        "deepcritical-native-locator-overlay-v1",
    ),
    "html_projection": ProductDefinition(
        "text/html",
        "https://html.spec.whatwg.org/",
        "html-living-standard",
    ),
    "docling_document": ProductDefinition(
        _JSON,
        "https://docling-project.github.io/docling/reference/docling_document/",
        "docling-document-v1",
    ),
    "docling_response": ProductDefinition(
        _JSON,
        "urn:docling:serve:conversion-response",
        "docling-serve-conversion-response-v1",
    ),
    "content_spans": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:content-span-set",
        "deepcritical-content-span-set-v1",
    ),
    "jats_locator_alignment": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:jats-locator-alignment",
        "deepcritical-jats-locator-alignment-v1",
    ),
    "bioc_locator_alignment": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:bioc-locator-alignment",
        "deepcritical-bioc-locator-alignment-v1",
    ),
    "runtime_attestation": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:runtime-attestation",
        "deepcritical-runtime-attestation-v1",
    ),
    "grobid_tei": ProductDefinition(
        "application/tei+xml",
        "https://tei-c.org/release/doc/tei-p5-doc/en/html/",
        "tei-p5",
    ),
    "searchable_pdf": ProductDefinition(
        "application/pdf",
        "https://pdfa.org/resource/iso-32000-pdf/",
        "iso-32000",
    ),
    "ocr_sidecar": ProductDefinition(
        "text/plain",
        "urn:deepcritical:document-processing:ocr-sidecar",
        "deepcritical-ocr-sidecar-v1",
    ),
    "ocr_log": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:ocr-log",
        "deepcritical-ocr-log-v1",
    ),
    "alignment_overlay": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:scholarly-alignment-overlay",
        "deepcritical-scholarly-alignment-overlay-v1",
    ),
    "content_integrity_overlay": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:content-integrity-overlay",
        "deepcritical-content-integrity-overlay-v1",
    ),
    "diagnostics_manifest": ProductDefinition(
        _JSON,
        "urn:deepcritical:document-processing:diagnostic-manifest",
        "deepcritical-processing-diagnostic-manifest-v1",
    ),
}

PRODUCT_REGISTRY: Mapping[str, ProductDefinition] = MappingProxyType(
    _PRODUCT_DEFINITIONS
)


def product_id_for(
    *,
    name: str,
    blob_sha256: str,
    producer_run_id: str,
) -> str:
    """Return the deterministic identity of one named immutable output."""

    digest = configuration_sha256(
        {
            "schema": "deepcritical-data-product-id-v1",
            "name": name,
            "blob_sha256": blob_sha256,
            "producer_run_id": producer_run_id,
        }
    )
    return f"product-{digest}"


def build_data_product_ref(
    *,
    name: str,
    blob_sha256: str,
    uri: str,
    byte_size: int,
    producer_run_id: str,
    source_artifact_ids: tuple[str, ...],
) -> DataProductRef:
    """Build a typed product reference from its registered contract."""

    definition = PRODUCT_REGISTRY.get(name)
    if definition is None:
        raise ValueError(f"unknown data product name: {name!r}")
    return DataProductRef(
        name=name,
        product_id=product_id_for(
            name=name,
            blob_sha256=blob_sha256,
            producer_run_id=producer_run_id,
        ),
        blob_sha256=blob_sha256,
        uri=uri,
        byte_size=byte_size,
        media_type=definition.media_type,
        payload_schema_uri=definition.payload_schema_uri,
        payload_schema_version=definition.payload_schema_version,
        producer_run_id=producer_run_id,
        source_artifact_ids=source_artifact_ids,
    )


def validate_product_contract(product: DataProductRef) -> None:
    """Reject a product whose declared media/schema does not match the registry."""

    definition = PRODUCT_REGISTRY.get(product.name)
    if definition is None:
        raise ValueError(f"unknown data product name: {product.name!r}")
    expected = (
        definition.media_type,
        definition.payload_schema_uri,
        definition.payload_schema_version,
    )
    actual = (
        product.media_type,
        product.payload_schema_uri,
        product.payload_schema_version,
    )
    if actual != expected:
        raise ValueError(
            f"data product {product.name!r} does not match its registered contract"
        )
    expected_product_id = product_id_for(
        name=product.name,
        blob_sha256=product.blob_sha256,
        producer_run_id=product.producer_run_id,
    )
    if product.product_id != expected_product_id:
        raise ValueError(f"data product {product.name!r} has an invalid product_id")


__all__ = [
    "PRODUCT_REGISTRY",
    "ProductDefinition",
    "build_data_product_ref",
    "product_id_for",
    "validate_product_contract",
]
