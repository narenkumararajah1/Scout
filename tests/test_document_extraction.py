"""Unit tests for backend/integrations/document_extraction.py (V3
Enhancements Phase 1 - PDF/website/text ingestion).

The PDF tests build a real PDF with reportlab (already a dependency for
report export) rather than checking in a binary fixture, so the test
exercises genuine pypdf extraction against a genuine PDF.

Network access is always mocked - no test here makes a real outbound
request.
"""

from unittest.mock import Mock, patch

import pytest

from backend.integrations.document_extraction import (
    MAX_UPLOAD_BYTES,
    ExtractionError,
    extract_from_bytes,
    extract_from_html,
    extract_from_pdf,
    extract_from_url,
    file_type_from_name,
)

_LONG_ENOUGH = (
    "Innominds delivers platform engineering, data and AI services to enterprise customers "
    "across healthcare, financial services and manufacturing industries worldwide."
)


def _build_pdf(text: str = _LONG_ENOUGH, pages: int = 1) -> bytes:
    from io import BytesIO

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for page in range(pages):
        # Wrapped manually - drawString does not wrap, and a single long
        # line would run off the page and out of the extracted text.
        vertical = 750
        for start in range(0, len(text), 70):
            pdf.drawString(72, vertical, f"{text[start:start + 70]}")
            vertical -= 14
        pdf.drawString(72, vertical - 14, f"Page marker {page}")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


# --- HTML ---------------------------------------------------------------


def test_html_extraction_returns_visible_text_title_and_description():
    html = f"""
    <html><head>
      <title>Data Engineering Services</title>
      <meta name="description" content="How Innominds builds data platforms." />
    </head><body>
      <h1>Data Engineering</h1>
      <p>{_LONG_ENOUGH}</p>
    </body></html>
    """

    extracted = extract_from_html(html)

    assert extracted.title == "Data Engineering Services"
    assert extracted.description == "How Innominds builds data platforms."
    assert "Data Engineering" in extracted.text
    assert "Innominds delivers platform engineering" in extracted.text


def test_html_extraction_excludes_script_and_style_content():
    html = f"""
    <html><body>
      <style>.hidden {{ color: #ff0000; font-weight: bold; }}</style>
      <script>var trackingId = 'GA-SHOULD-NOT-APPEAR';</script>
      <p>{_LONG_ENOUGH}</p>
    </body></html>
    """

    extracted = extract_from_html(html)

    assert "GA-SHOULD-NOT-APPEAR" not in extracted.text
    assert "font-weight" not in extracted.text
    assert "Innominds delivers" in extracted.text


def test_html_extraction_preserves_paragraph_breaks_for_chunking():
    html = f"<html><body><p>{_LONG_ENOUGH}</p><p>{_LONG_ENOUGH}</p></body></html>"

    assert "\n\n" in extract_from_html(html).text


def test_html_with_almost_no_text_is_rejected_as_a_probable_js_shell():
    with pytest.raises(ExtractionError, match="too little readable text"):
        extract_from_html("<html><body><div id='root'></div></body></html>")


def test_stray_closing_tag_does_not_suppress_real_content():
    # A malformed page must not drive the skip counter negative and start
    # discarding everything after it.
    html = f"</script><html><body><p>{_LONG_ENOUGH}</p></body></html>"

    assert "Innominds delivers" in extract_from_html(html).text


# --- PDF ----------------------------------------------------------------


def test_pdf_extraction_returns_text_and_page_count():
    extracted = extract_from_pdf(_build_pdf(pages=3))

    assert extracted.page_count == 3
    assert "Innominds" in extracted.text
    assert "Page marker 2" in extracted.text


def test_pdf_placeholder_author_metadata_is_treated_as_absent():
    # reportlab (and most authoring tools) write "(anonymous)" into the
    # author field when it was never set. Storing that verbatim would show
    # a fabricated author in the Library.
    extracted = extract_from_pdf(_build_pdf(pages=1))

    assert extracted.author is None


def test_pdf_real_author_metadata_is_preserved():
    from io import BytesIO

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setAuthor("Priya Raman")
    pdf.setTitle("Platform Engineering Overview")
    pdf.drawString(100, 700, _LONG_ENOUGH)
    pdf.save()

    extracted = extract_from_pdf(buffer.getvalue())

    assert extracted.author == "Priya Raman"
    assert extracted.title == "Platform Engineering Overview"


def test_pdf_with_no_extractable_text_is_reported_as_needing_ocr():
    # A valid PDF with no text objects stands in for a scanned document.
    from io import BytesIO

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.showPage()
    pdf.save()

    with pytest.raises(ExtractionError, match="scanned image"):
        extract_from_pdf(buffer.getvalue())


def test_unreadable_bytes_are_reported_rather_than_crashing():
    with pytest.raises(ExtractionError, match="Could not read PDF"):
        extract_from_pdf(b"this is definitely not a pdf")


# --- Dispatch and validation -------------------------------------------


def test_dispatch_routes_each_supported_type():
    assert "Innominds" in extract_from_bytes(_LONG_ENOUGH.encode(), "txt").text
    assert "Innominds" in extract_from_bytes(_LONG_ENOUGH.encode(), "md").text
    assert "Innominds" in extract_from_bytes(f"<p>{_LONG_ENOUGH}</p>".encode(), "html").text
    assert "Innominds" in extract_from_bytes(_build_pdf(), "pdf").text


def test_extension_is_matched_case_insensitively_and_with_a_leading_dot():
    assert extract_from_bytes(_LONG_ENOUGH.encode(), "TXT").text
    assert extract_from_bytes(_LONG_ENOUGH.encode(), ".txt").text


def test_unsupported_type_is_rejected():
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        extract_from_bytes(b"content", "docx")


def test_empty_file_is_rejected():
    with pytest.raises(ExtractionError, match="empty"):
        extract_from_bytes(b"", "txt")


def test_oversized_file_is_rejected_before_parsing():
    with pytest.raises(ExtractionError, match="ingestion limit"):
        extract_from_bytes(b"x" * (MAX_UPLOAD_BYTES + 1), "txt")


def test_non_utf8_bytes_fall_back_rather_than_failing():
    # latin-1 encoded text must not lose the whole document.
    extracted = extract_from_bytes(f"Rôle: {_LONG_ENOUGH}".encode("latin-1"), "txt")

    assert "Innominds delivers" in extracted.text


def test_file_type_from_name():
    assert file_type_from_name("brochure.PDF") == "pdf"
    assert file_type_from_name("notes.txt") == "txt"
    assert file_type_from_name("archive.tar.gz") == "gz"
    assert file_type_from_name("no_extension") == ""
    assert file_type_from_name("") == ""


# --- Website ------------------------------------------------------------


def _mock_response(body: bytes, content_type: str = "text/html", status: int = 200) -> Mock:
    response = Mock()
    response.headers = {"Content-Type": content_type}
    response.status_code = status
    response.iter_content = Mock(return_value=[body])
    response.raise_for_status = Mock()
    response.close = Mock()
    return response


def test_url_extraction_fetches_and_parses_a_page():
    html = f"<html><head><title>Cloud Practice</title></head><body><p>{_LONG_ENOUGH}</p></body></html>"

    with patch("backend.integrations.document_extraction.requests.get", return_value=_mock_response(html.encode())):
        extracted = extract_from_url("https://www.innominds.com/services/cloud")

    assert extracted.title == "Cloud Practice"
    assert "Innominds delivers" in extracted.text


def test_url_extraction_handles_a_pdf_response():
    with patch(
        "backend.integrations.document_extraction.requests.get",
        return_value=_mock_response(_build_pdf(), content_type="application/pdf"),
    ):
        extracted = extract_from_url("https://www.innominds.com/brochure.pdf")

    assert "Innominds" in extracted.text


def test_url_extraction_derives_a_readable_title_when_the_page_has_none():
    html = f"<html><body><p>{_LONG_ENOUGH}</p></body></html>"

    with patch("backend.integrations.document_extraction.requests.get", return_value=_mock_response(html.encode())):
        extracted = extract_from_url("https://www.innominds.com/services/data-engineering")

    assert extracted.title == "Data Engineering"


def test_non_http_schemes_are_rejected_without_a_request():
    with patch("backend.integrations.document_extraction.requests.get") as get:
        with pytest.raises(ExtractionError, match="Only http"):
            extract_from_url("file:///etc/passwd")
    get.assert_not_called()


def test_network_failure_is_reported_as_an_extraction_error():
    import requests as requests_module

    with patch(
        "backend.integrations.document_extraction.requests.get",
        side_effect=requests_module.ConnectionError("name resolution failed"),
    ):
        with pytest.raises(ExtractionError, match="Could not fetch"):
            extract_from_url("https://nonexistent.invalid/page")


def test_oversized_response_is_abandoned_mid_stream():
    from backend.integrations.document_extraction import MAX_WEBSITE_BYTES

    oversized = Mock()
    oversized.headers = {"Content-Type": "text/html"}
    oversized.raise_for_status = Mock()
    oversized.close = Mock()
    # Two blocks that together exceed the cap - streaming must bail rather
    # than buffering the whole thing.
    oversized.iter_content = Mock(return_value=[b"x" * MAX_WEBSITE_BYTES, b"x" * 1024])

    with patch("backend.integrations.document_extraction.requests.get", return_value=oversized):
        with pytest.raises(ExtractionError, match="fetch limit"):
            extract_from_url("https://example.com/huge")


def test_unsupported_content_type_is_rejected():
    with patch(
        "backend.integrations.document_extraction.requests.get",
        return_value=_mock_response(b"\x00\x01", content_type="image/png"),
    ):
        with pytest.raises(ExtractionError, match="Unsupported content type"):
            extract_from_url("https://example.com/logo.png")
