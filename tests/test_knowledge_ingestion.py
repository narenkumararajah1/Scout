import uuid

import chromadb

from backend.database.chroma import get_embedding_function
from backend.knowledge_ingestion import ingest_documents


def _empty_test_collection():
    # EphemeralClient shares state by collection name within a process, so
    # each test gets a uniquely-named collection for true isolation. Never
    # touches the real persistent data/chroma directory either way.
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(
        name=f"test_knowledge_{uuid.uuid4().hex}", embedding_function=get_embedding_function()
    )


def test_ingest_documents_returns_zero_for_missing_directory(tmp_path):
    collection = _empty_test_collection()

    count = ingest_documents(
        source_dir=str(tmp_path / "does_not_exist"), collection=collection
    )

    assert count == 0
    assert collection.count() == 0


def test_ingest_documents_returns_zero_for_empty_directory(tmp_path):
    collection = _empty_test_collection()

    count = ingest_documents(source_dir=str(tmp_path), collection=collection)

    assert count == 0
    assert collection.count() == 0


def test_ingest_documents_upserts_txt_and_md_files(tmp_path):
    (tmp_path / "case_study.txt").write_text("Innominds helped a retailer migrate to the cloud.")
    (tmp_path / "service_offering.md").write_text("# AI Consulting\nInnominds offers AI consulting.")
    (tmp_path / "ignored.pdf").write_bytes(b"%PDF-not-a-real-pdf")

    collection = _empty_test_collection()

    count = ingest_documents(source_dir=str(tmp_path), collection=collection)

    assert count == 2
    assert collection.count() == 2

    stored = collection.get()
    assert set(stored["ids"]) == {"case_study.txt", "service_offering.md"}


def test_ingest_documents_skips_unreadable_files_without_crashing(tmp_path):
    (tmp_path / "good.txt").write_text("Innominds helped a retailer migrate to the cloud.")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe\x00\x00not valid utf-8")

    collection = _empty_test_collection()

    count = ingest_documents(source_dir=str(tmp_path), collection=collection)

    assert count == 1
    assert collection.count() == 1
    stored = collection.get()
    assert stored["ids"] == ["good.txt"]


def test_ingest_documents_is_idempotent(tmp_path):
    (tmp_path / "case_study.txt").write_text("Original content.")
    collection = _empty_test_collection()

    ingest_documents(source_dir=str(tmp_path), collection=collection)

    (tmp_path / "case_study.txt").write_text("Updated content.")
    ingest_documents(source_dir=str(tmp_path), collection=collection)

    assert collection.count() == 1
    stored = collection.get(ids=["case_study.txt"])
    assert stored["documents"][0] == "Updated content."
