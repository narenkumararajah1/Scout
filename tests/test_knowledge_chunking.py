"""Unit tests for backend/ai/knowledge_chunking.py (V3 Enhancements
Phase 1 - Company Knowledge Engine).

Pure text processing: no Postgres, no ChromaDB, no LLM, so these run
everywhere unconditionally.
"""

import pytest

from backend.ai.knowledge_chunking import (
    DEFAULT_CHUNK_SIZE,
    MIN_CHUNK_CHARS,
    chunk_text,
    normalize_text,
)


def test_empty_and_whitespace_input_produce_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  \t ") == []


def test_short_document_becomes_a_single_chunk():
    chunks = chunk_text("Innominds delivers platform engineering services to healthcare providers.")

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert "platform engineering" in chunks[0].text


def test_long_document_is_split_into_multiple_bounded_chunks():
    # 60 distinct paragraphs, comfortably past one chunk's worth.
    document = "\n\n".join(f"Paragraph {n} describes a distinct engagement outcome." for n in range(60))

    chunks = chunk_text(document)

    assert len(chunks) > 1
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    # Overlap can carry a little past the nominal size, and a short tail
    # gets folded back into its predecessor - so this asserts the bound is
    # respected with slack rather than exactly.
    assert all(len(chunk.text) <= DEFAULT_CHUNK_SIZE * 2 for chunk in chunks)


def test_consecutive_chunks_overlap_so_boundary_passages_stay_retrievable():
    document = "\n\n".join(f"Sentence number {n} about cloud migration delivery." for n in range(60))

    chunks = chunk_text(document, chunk_size=400, overlap=120)

    assert len(chunks) >= 3
    # The tail of one chunk should reappear at the head of the next.
    first_tail_words = chunks[0].text.split()[-4:]
    assert any(word in chunks[1].text for word in first_tail_words)


def test_a_paragraph_longer_than_one_chunk_is_split_without_breaking_words():
    single_long_paragraph = " ".join(["knowledge"] * 500)

    chunks = chunk_text(single_long_paragraph, chunk_size=300, overlap=50)

    assert len(chunks) > 1
    # Every chunk must contain only whole copies of the word - a mid-word
    # split would leave fragments like "knowled".
    for chunk in chunks:
        assert set(chunk.text.split()) == {"knowledge"}


def test_text_with_no_sentence_punctuation_still_splits_on_words():
    # Extracted tables and bullet runs often have no . ! or ? at all.
    chunks = chunk_text(" ".join(f"row{n}" for n in range(400)), chunk_size=200, overlap=40)

    assert len(chunks) > 1
    assert all(chunk.text.strip() for chunk in chunks)


def test_short_trailing_fragment_is_folded_into_the_previous_chunk():
    body = "\n\n".join(f"Paragraph {n} with a reasonable amount of substantive content." for n in range(20))
    document = f"{body}\n\nThanks."

    chunks = chunk_text(document, chunk_size=300, overlap=60)

    assert len(chunks) >= 2
    # "Thanks." is well under MIN_CHUNK_CHARS, so it must not be its own
    # chunk competing for a retrieval slot.
    assert not any(chunk.text.strip() == "Thanks." for chunk in chunks)
    assert "Thanks." in chunks[-1].text
    assert len("Thanks.") < MIN_CHUNK_CHARS


def test_overlap_not_smaller_than_chunk_size_is_rejected():
    # Would never advance through the document - a config bug worth raising on.
    with pytest.raises(ValueError, match="overlap must be smaller"):
        chunk_text("some text here", chunk_size=100, overlap=100)


def test_normalize_text_collapses_extraction_noise_but_keeps_paragraphs():
    messy = "Line   one\r\n\r\n\r\n\r\nLine    two\t\there  "

    normalized = normalize_text(messy)

    assert "\r" not in normalized
    assert "   " not in normalized
    # Paragraph separation survives - it is chunking's best split signal.
    assert "\n\n" in normalized
    assert normalized.startswith("Line one")


def test_chunking_is_deterministic():
    document = "\n\n".join(f"Paragraph {n} of the whitepaper." for n in range(40))

    assert [c.text for c in chunk_text(document)] == [c.text for c in chunk_text(document)]
