"""Document chunking for the Company Knowledge Engine (V3 Enhancements
Phase 1 - 03_COMPANY_KNOWLEDGE_ENGINE.md's "Chunking" pipeline stage).

Why this exists: backend/knowledge_ingestion.py has always embedded each
source file as one single Chroma document. For the .txt notes the
knowledge_sources_dir was originally seeded with that was adequate, but
the corpus this phase opens the door to - PDF whitepapers, service
brochures, multi-page case studies - breaks it. One embedding averaged
over twenty pages is close to meaningless: it retrieves for no query in
particular, and the specific passage a query actually needed can never
be returned on its own. Chunking is what makes retrieval quality track
corpus size instead of degrading with it.

Chunks overlap so a passage split across a boundary is still retrievable
whole from at least one chunk. Splitting prefers paragraph breaks, then
sentence ends, then word boundaries - never mid-word, which would put a
fragment into the embedding space that no real query resembles.

No LLM call and no I/O: this is deterministic text processing, cheap
enough to run on every ingestion and trivially unit-testable.
"""

import re
from dataclasses import dataclass

# Sized in characters rather than tokens: the embedding model here is
# all-MiniLM-L6-v2 (backend/database/chroma.py), whose 256-word-piece
# input limit works out near 1000 characters of ordinary English prose.
# Deliberately just under that - a chunk longer than the model's window
# is silently truncated at embedding time, which loses its tail without
# reporting anything.
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150

# Below this, a trailing chunk is folded back into its predecessor rather
# than embedded alone. A 40-character fragment ("Contact us for details.")
# is noise that competes with real content for retrieval slots.
MIN_CHUNK_CHARS = 80

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_EXCESS_WHITESPACE = re.compile(r"[ \t]{2,}")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class Chunk:
    """One embeddable passage. `index` is its ordinal within the document,
    used to build the stable Chroma id `document:<doc_id>:<index>`.
    """

    index: int
    text: str


def normalize_text(text: str) -> str:
    """Collapses the whitespace noise that PDF and HTML extraction leave
    behind, without destroying paragraph structure (which is the best
    split signal chunking has).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _EXCESS_WHITESPACE.sub(" ", text)
    text = _EXCESS_NEWLINES.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def _split_oversized(segment: str, chunk_size: int) -> list:
    """Splits a single segment that is itself longer than chunk_size.

    Tries sentence boundaries first and falls back to word boundaries for
    text with no sentence punctuation at all (extracted tables, bullet
    lists, headings runs). Never splits inside a word.
    """
    pieces: list = []
    for sentence in _SENTENCE_END.split(segment):
        if len(sentence) <= chunk_size:
            pieces.append(sentence)
            continue
        current = ""
        for word in sentence.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > chunk_size and current:
                pieces.append(current)
                current = word
            else:
                current = candidate
        if current:
            pieces.append(current)
    return [piece for piece in pieces if piece]


def _tail_overlap(text: str, overlap: int) -> str:
    """Returns the last `overlap` characters of text, trimmed forward to
    the next word boundary so the carried context never starts mid-word.
    """
    if overlap <= 0 or len(text) <= overlap:
        return text
    tail = text[-overlap:]
    space = tail.find(" ")
    return tail[space + 1 :] if space != -1 else tail


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list:
    """Splits text into overlapping chunks at natural boundaries.

    Returns [] for empty or whitespace-only input - an empty list means
    "nothing to index", which the ingestion service reports as a failed
    extraction rather than silently recording a document with zero chunks
    as ready.
    """
    normalized = normalize_text(text)
    if not normalized:
        return []
    if overlap >= chunk_size:
        # Would never advance through the document; a caller passing this
        # has a configuration bug worth surfacing loudly.
        raise ValueError("overlap must be smaller than chunk_size")

    segments: list = []
    for paragraph in _PARAGRAPH_BREAK.split(normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= chunk_size:
            segments.append(paragraph)
        else:
            segments.extend(_split_oversized(paragraph, chunk_size))

    chunks: list = []
    current = ""
    for segment in segments:
        candidate = f"{current}\n\n{segment}".strip() if current else segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            carried = _tail_overlap(current, overlap)
            current = f"{carried}\n\n{segment}".strip() if carried else segment
            # The carried overlap can itself push the new chunk over the
            # limit; emit the overlap-free segment alone in that case
            # rather than exceeding chunk_size.
            if len(current) > chunk_size:
                current = segment
        else:
            current = segment

    if current:
        # Fold a too-short tail back into the previous chunk. The combined
        # length can exceed chunk_size slightly, which costs a little
        # truncation risk on one chunk and is the better trade against
        # putting a meaningless fragment into the index.
        if chunks and len(current) < MIN_CHUNK_CHARS:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)

    return [Chunk(index=index, text=chunk) for index, chunk in enumerate(chunks)]
