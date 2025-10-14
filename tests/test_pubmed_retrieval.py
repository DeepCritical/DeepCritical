from datetime import datetime, timezone

import pytest

from DeepResearch.src.datatypes.bioinformatics import PubMedPaper
from DeepResearch.src.tools.bioinformatics_tools import (
    _build_paper,
    _extract_text_from_bioc,
    _get_fulltext,
    _get_metadata,
    pubmed_paper_retriever,
)

# Mock Data


def setup_mock_requests(requests_mock):
    """Fixture to mock requests to NCBI and other APIs."""
    # Mock for pubmed_paper_retriever (esearch)
    requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        json={"esearchresult": {"idlist": ["12345", "67890"]}},
    )

    # Mock for _get_metadata (esummary)
    requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345&retmode=json",
        json={
            "result": {
                "12345": {
                    "title": "Test Paper 1",
                    "fulljournalname": "Journal of Testing",
                    "pubdate": "2023",
                    "authors": [{"name": "Author One"}],
                    "pmcid": "PMC12345",
                }
            }
        },
    )
    requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=67890&retmode=json",
        json={
            "result": {
                "67890": {
                    "title": "Test Paper 2",
                    "fulljournalname": "Journal of Mocking",
                    "pubdate": "2024",
                    "authors": [{"name": "Author Two"}],
                }
            }
        },
    )

    # Mock for _get_fulltext (BioC)
    requests_mock.get(
        "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/12345/unicode",
        json={
            "documents": [
                {
                    "passages": [
                        {
                            "infons": {"section_type": "ABSTRACT", "type": "abstract"},
                            "text": "This is the abstract.",
                        },
                        {
                            "infons": {"section_type": "INTRO", "type": "paragraph"},
                            "text": "This is the introduction.",
                        },
                    ]
                }
            ]
        },
    )
    requests_mock.get(
        "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/67890/unicode",
        status_code=404,
    )
    return requests_mock


def test_pubmed_paper_retriever_success(requests_mock):
    """Test successful retrieval of papers."""
    setup_mock_requests(requests_mock)
    papers = pubmed_paper_retriever("test query")
    assert len(papers) == 2
    assert papers[0].pmid == "12345"
    assert papers[0].title == "Test Paper 1"
    assert papers[1].pmid == "67890"
    assert papers[1].title == "Test Paper 2"


def test_pubmed_paper_retriever_api_error(requests_mock):
    """Test API error during paper retrieval."""
    requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        status_code=500,
    )
    papers = pubmed_paper_retriever("test query")
    assert len(papers) == 0


@pytest.mark.usefixtures("disable_ratelimiter")
def test_get_metadata_success(requests_mock):
    """Test successful metadata retrieval."""
    setup_mock_requests(requests_mock)
    metadata = _get_metadata(12345)
    assert metadata is not None
    assert metadata["result"]["12345"]["title"] == "Test Paper 1"


def test_get_metadata_error(requests_mock):
    """Test error during metadata retrieval."""
    requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345&retmode=json",
        status_code=500,
    )
    metadata = _get_metadata(12345)
    assert metadata is None


@pytest.mark.usefixtures("disable_ratelimiter")
def test_get_fulltext_success(requests_mock):
    """Test successful full-text retrieval."""
    setup_mock_requests(requests_mock)
    fulltext = _get_fulltext(12345)
    assert fulltext is not None
    assert "documents" in fulltext


def test_get_fulltext_error(requests_mock):
    """Test error during full-text retrieval."""
    setup_mock_requests(requests_mock)
    fulltext = _get_fulltext(67890)
    assert fulltext is None


def test_extract_text_from_bioc():
    """Test extraction of text from BioC JSON."""
    bioc_data = {
        "documents": [
            {
                "passages": [
                    {
                        "infons": {"section_type": "INTRO", "type": "paragraph"},
                        "text": "First paragraph.",
                    },
                    {
                        "infons": {"section_type": "INTRO", "type": "paragraph"},
                        "text": "Second paragraph.",
                    },
                ]
            }
        ]
    }
    text = _extract_text_from_bioc(bioc_data)
    assert text == "First paragraph.\nSecond paragraph."


def test_extract_text_from_bioc_empty():
    """Test extraction with empty or invalid BioC data."""
    assert _extract_text_from_bioc({}) == ""
    assert _extract_text_from_bioc({"documents": []}) == ""


def test_build_paper(monkeypatch):
    """Test building a PubMedPaper object."""
    monkeypatch.setattr(
        "DeepResearch.src.tools.bioinformatics_tools._get_metadata",
        lambda pmid: {
            "result": {
                "999": {
                    "title": "Built Paper",
                    "fulljournalname": "Journal of Building",
                    "pubdate": "2025",
                    "authors": [{"name": "Builder Bob"}],
                    "pmcid": "PMC999",
                }
            }
        },
    )
    monkeypatch.setattr(
        "DeepResearch.src.tools.bioinformatics_tools._get_fulltext",
        lambda pmid: {
            "documents": [{"passages": [{"text": "Abstract of built paper."}]}]
        },
    )

    paper = _build_paper(999)
    assert isinstance(paper, PubMedPaper)
    assert paper.title == "Built Paper"
    assert paper.abstract == "Abstract of built paper."
    assert paper.is_open_access
    assert paper.publication_date == datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_build_paper_no_metadata(monkeypatch):
    """Test building a paper when metadata is missing."""
    monkeypatch.setattr(
        "DeepResearch.src.tools.bioinformatics_tools._get_metadata", lambda pmid: None
    )
    paper = _build_paper(999)
    assert paper is None
