from lxml import etree

from DeepResearch.src.document_processing.adapters import JATSLocatorAdapter


def test_namespace_qualified_jats_xpath_is_self_contained_and_resolves() -> None:
    content = b"""<article xmlns="urn:nlm:niso:jats:1.3">
      <body><sec><p>Namespace-aware evidence.</p></sec></body>
    </article>"""

    locator = JATSLocatorAdapter().extract_locators(content)[0]
    root = etree.fromstring(content)

    assert locator.xpath is not None
    assert "local-name()" in locator.xpath
    assert "namespace-uri()" in locator.xpath
    resolved = root.xpath(locator.xpath)
    assert len(resolved) == 1
    assert " ".join(resolved[0].itertext()).strip() == "Namespace-aware evidence."
