"""Content extraction for the Company Knowledge Engine (V3 Enhancements
Phase 1 - 03_COMPANY_KNOWLEDGE_ENGINE.md's "Content Extraction" stage).

Turns a source - uploaded bytes or a URL - into plain text plus whatever
metadata the format volunteers (PDF title/author, HTML <title>/meta
description). Chunking, embedding and persistence are all downstream of
this and live elsewhere; this module knows about file formats and nothing
about ChromaDB or Postgres.

Placed under backend/integrations/ rather than backend/ai/ because the
website path performs real outbound network I/O, which is what that
package already isolates (see glean_client.py). Every function here
raises ExtractionError on failure rather than returning empty text: the
ingestion service records the reason on the document row so the Library
can show *why* a document failed, per 04_KNOWLEDGE_LIBRARY.md's
"Review ingestion failures".
"""

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import BytesIO
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Formats 04_KNOWLEDGE_LIBRARY.md's "Supported Content" lists, minus Word
# (explicitly marked "(future)" there). Extending this is one entry plus
# one branch in extract_from_bytes.
SUPPORTED_FILE_TYPES = ("pdf", "txt", "md", "html", "htm")

# A marketing page or brochure that yields less than this after tag
# stripping produced navigation chrome, a cookie banner, or a JS-rendered
# shell - not knowledge. Treated as a failure so it shows up in the
# Library as one instead of silently entering the corpus as an empty
# document that pollutes retrieval.
MIN_EXTRACTED_CHARS = 100

WEBSITE_FETCH_TIMEOUT_SECONDS = 20
# Guards against a mis-typed URL pointing at a multi-gigabyte file: the
# response is streamed and abandoned once it exceeds this.
MAX_WEBSITE_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Redirect hops, each of which is re-checked against _assert_public_host.
MAX_REDIRECTS = 5

_USER_AGENT = "Scout-KnowledgeEngine/1.0"


def _assert_public_host(hostname: str) -> None:
    """Rejects a URL that resolves to an address inside the deployment.

    Website ingestion takes a URL from a user and fetches it *from the
    server*, which makes it a request forgery primitive unless the target
    is constrained. The address that matters most is 169.254.169.254: on
    every major cloud that is the instance metadata service, and on a
    default-configured host it hands out the machine's own IAM
    credentials to anything that asks. Loopback and private ranges are
    equally wrong - they expose internal services that are only
    unauthenticated because they were never meant to be reachable.

    Resolution happens here rather than pattern-matching the hostname,
    because a name that merely *looks* external can resolve to a private
    address. Every resolved address must be public: a host with one
    public and one private A record is still a way in.

    This is not a full SSRF defence - the address can change between this
    check and the fetch - but it closes the trivially exploitable form
    while keeping the feature usable for the public documentation pages
    it exists to ingest.
    """
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ExtractionError(f"Could not resolve {hostname}: {exc}") from exc

    for info in resolved:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise ExtractionError(
                f"{hostname} resolves to a non-public address ({address}). "
                "Only publicly reachable pages can be ingested."
            )


class ExtractionError(Exception):
    """Raised when a source cannot be turned into usable text."""


@dataclass
class ExtractedDocument:
    text: str
    # Metadata the format itself supplied. Never overrides what a user
    # typed on the upload form - the ingestion service treats these
    # strictly as fallbacks.
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    page_count: Optional[int] = None
    warnings: list = field(default_factory=list)


class _TextExtractingHTMLParser(HTMLParser):
    """Collects visible text and <title>/<meta name="description"> from
    an HTML document.

    Uses the standard library rather than adding BeautifulSoup: the job
    here is "give me the visible words", not DOM traversal, and stdlib
    keeps the dependency surface flat - this repo has already been bitten
    by transitive-dependency conflicts (see requirements.txt's
    opentelemetry pin). If real Innominds pages later turn out to need
    smarter main-content detection, that is the point to reconsider.
    """

    _SKIP_CONTENT_TAGS = {"script", "style", "noscript", "template", "svg"}
    # Tags whose boundaries are paragraph breaks, so chunking downstream
    # still has structure to split on after markup is gone.
    _BLOCK_TAGS = {
        "p", "div", "section", "article", "header", "footer", "main", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "blockquote", "pre", "table",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list = []
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_CONTENT_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attributes = dict(attrs)
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            if name in ("description", "og:description") and not self.description:
                self.description = (attributes.get("content") or "").strip() or None
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_CONTENT_TAGS:
            # Clamped at zero: malformed markup with a stray closing tag
            # must not drive this negative and start skipping real content.
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title = (self.title or "") + data
            return
        if data.strip():
            self.parts.append(data)

    def extracted_text(self) -> str:
        return "".join(self.parts)


def extract_from_html(html: str) -> ExtractedDocument:
    parser = _TextExtractingHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # html.parser raises on some malformed input
        raise ExtractionError(f"Could not parse HTML: {exc}") from exc

    text = parser.extracted_text()
    if len(text.strip()) < MIN_EXTRACTED_CHARS:
        raise ExtractionError(
            "HTML produced too little readable text - the page may require JavaScript "
            "to render, or may be a redirect or consent wall rather than content."
        )
    return ExtractedDocument(
        text=text,
        title=(parser.title or "").strip() or None,
        description=parser.description,
    )


# Values authoring tools write into PDF metadata when the field was never
# filled in. Storing these verbatim puts a fake author like "(anonymous)"
# on a document and shows it in the Library as though it were real, so they
# are treated as absent. Compared case-insensitively after stripping.
_PLACEHOLDER_METADATA_VALUES = frozenset(
    {
        "(anonymous)",
        "anonymous",
        "unknown",
        "untitled",
        "none",
        "n/a",
        "-",
    }
)


def _clean_metadata_value(value) -> Optional[str]:
    """Normalizes a format-supplied metadata value, dropping placeholders."""
    cleaned = (str(value) if value is not None else "").strip()
    if not cleaned or cleaned.lower() in _PLACEHOLDER_METADATA_VALUES:
        return None
    return cleaned


def extract_from_pdf(data: bytes) -> ExtractedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise ExtractionError(
            "PDF support requires the 'pypdf' package (see requirements.txt)."
        ) from exc

    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read PDF: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        # Some PDFs are encrypted with an empty owner password and open
        # fine once decrypt("") is called; a real password is a genuine
        # failure the Library should report rather than guess at.
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ExtractionError("PDF is password-protected and cannot be indexed.") from exc

    pages: list = []
    warnings: list = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:
            # One malformed page must not lose the other 39.
            logger.warning("Skipping unreadable PDF page %d: %s", number, exc)
            warnings.append(f"Page {number} could not be read and was skipped.")

    text = "\n\n".join(part for part in pages if part.strip())
    if len(text.strip()) < MIN_EXTRACTED_CHARS:
        raise ExtractionError(
            "PDF produced no extractable text - it is most likely a scanned image, "
            "which needs OCR before it can be indexed."
        )

    info = getattr(reader, "metadata", None) or {}
    return ExtractedDocument(
        text=text,
        title=_clean_metadata_value(getattr(info, "title", None)),
        author=_clean_metadata_value(getattr(info, "author", None)),
        page_count=len(reader.pages),
        warnings=warnings,
    )


def extract_from_bytes(data: bytes, file_type: str) -> ExtractedDocument:
    """Dispatches to the extractor for `file_type` (extension, no dot)."""
    normalized = (file_type or "").lower().lstrip(".")
    if normalized not in SUPPORTED_FILE_TYPES:
        raise ExtractionError(
            f"Unsupported file type '{file_type}'. Supported: {', '.join(SUPPORTED_FILE_TYPES)}."
        )
    if len(data) > MAX_UPLOAD_BYTES:
        raise ExtractionError(
            f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB ingestion limit."
        )
    if not data:
        raise ExtractionError("File is empty.")

    if normalized == "pdf":
        return extract_from_pdf(data)
    if normalized in ("html", "htm"):
        return extract_from_html(_decode_text(data))

    text = _decode_text(data)
    if len(text.strip()) < MIN_EXTRACTED_CHARS:
        raise ExtractionError("File contains too little text to be worth indexing.")
    return ExtractedDocument(text=text)


def _decode_text(data: bytes) -> str:
    """Decodes bytes as UTF-8, falling back to latin-1.

    latin-1 cannot fail on any byte sequence, so this never raises - a
    mis-detected encoding yields mojibake in a few characters, which is a
    far better outcome for a knowledge corpus than rejecting an entire
    otherwise-valid document.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        logger.info("Falling back to latin-1 decoding for a non-UTF-8 source document.")
        return data.decode("latin-1", errors="replace")


def extract_from_url(url: str) -> ExtractedDocument:
    """Fetches a URL and extracts its text (03_COMPANY_KNOWLEDGE_ENGINE.md's
    "Website ingestion" - the Innominds site's service, practice and
    industry pages are named there as primary knowledge sources).

    Single page only, deliberately: no crawling, no link following. A
    crawler needs robots.txt handling, rate limiting and scope rules to be
    responsible, and the documented sources are specific pages an
    administrator names, not a whole site to walk.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ExtractionError("Only http:// and https:// URLs can be ingested.")
    if not parsed.hostname:
        raise ExtractionError("URL is missing a hostname.")
    _assert_public_host(parsed.hostname)

    # Redirects are followed by hand so that every hop is checked. With
    # requests' automatic redirect handling, a public URL that returns a
    # 302 to http://169.254.169.254/ defeats the check above entirely -
    # only the first host is ever seen.
    try:
        response = None
        for _ in range(MAX_REDIRECTS + 1):
            response = requests.get(
                url,
                timeout=WEBSITE_FETCH_TIMEOUT_SECONDS,
                headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/pdf,text/plain"},
                stream=True,
                allow_redirects=False,
            )
            if not response.is_redirect:
                break
            location = response.headers.get("Location", "")
            response.close()
            url = requests.compat.urljoin(url, location)
            hop = urlparse(url)
            if hop.scheme not in ("http", "https") or not hop.hostname:
                raise ExtractionError(f"Redirect to an unsupported URL: {location}")
            _assert_public_host(hop.hostname)
        else:
            raise ExtractionError(f"Too many redirects (more than {MAX_REDIRECTS}).")
    except requests.RequestException as exc:
        raise ExtractionError(f"Could not fetch {url}: {exc}") from exc

    # stream=True holds the connection open until the body is consumed, so
    # every path below - including the size-limit bail-out - must close it.
    try:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ExtractionError(f"Could not fetch {url}: {exc}") from exc

        chunks: list = []
        total = 0
        try:
            for block in response.iter_content(chunk_size=64 * 1024):
                total += len(block)
                if total > MAX_WEBSITE_BYTES:
                    raise ExtractionError(
                        f"Page exceeds the {MAX_WEBSITE_BYTES // (1024 * 1024)}MB fetch limit."
                    )
                chunks.append(block)
        except requests.RequestException as exc:
            # A connection dropped mid-body, not at request time.
            raise ExtractionError(f"Could not fetch {url}: {exc}") from exc
        body = b"".join(chunks)
        content_type = (response.headers.get("Content-Type") or "").lower()
    finally:
        response.close()

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        extracted = extract_from_pdf(body)
    elif "html" in content_type or not content_type:
        extracted = extract_from_html(_decode_text(body))
    elif content_type.startswith("text/"):
        text = _decode_text(body)
        if len(text.strip()) < MIN_EXTRACTED_CHARS:
            raise ExtractionError("Page contains too little text to be worth indexing.")
        extracted = ExtractedDocument(text=text)
    else:
        raise ExtractionError(f"Unsupported content type '{content_type}' at {url}.")

    if not extracted.title:
        # Last-resort title so the Library never shows a blank row: the
        # final path segment usually reads well enough
        # ("/services/data-engineering" -> "Data Engineering").
        slug = (parsed.path.rstrip("/").rsplit("/", 1)[-1] or parsed.netloc)
        extracted.title = re.sub(r"[-_]+", " ", slug).strip().title() or parsed.netloc
    return extracted


def file_type_from_name(filename: str) -> str:
    """Extension (no dot, lowercase) from a filename, "" if it has none."""
    _, _, extension = (filename or "").rpartition(".")
    return extension.lower() if extension and extension != filename else ""
