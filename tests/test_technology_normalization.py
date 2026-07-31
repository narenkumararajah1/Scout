"""Tests for backend/services/technology_normalization.py.

Written against real extractor output. After three NVIDIA analyses the
live data contained Omniverse/NVIDIA Omniverse, Riva/NVIDIA Riva,
NIM/NVIDIA NIM, NeMo/NeMo framework and Grace/Grace CPUs as separate
rows - and, in the same list, NeMo/NeMo Retriever and Quantum/Quantum
InfiniBand, which are *different products*.

Roughly half of these tests assert that things do NOT merge. That balance
is deliberate: a missed merge costs a little confidence, while a wrong
merge silently corrupts history that nothing downstream can repair.
"""

from backend.services.technology_normalization import canonical_name, preferred_display_name


def _same(a: str, b: str, company: str = "NVIDIA") -> bool:
    return canonical_name(a, company) == canonical_name(b, company)


# --- Merges that should happen -----------------------------------------


def test_the_companys_own_name_as_a_prefix_is_stripped():
    assert _same("NVIDIA Omniverse", "Omniverse")
    assert _same("NVIDIA Riva", "Riva")
    assert _same("NVIDIA NIM", "NIM")


def test_a_trailing_generic_descriptor_is_stripped():
    assert _same("NeMo framework", "NeMo")
    assert _same("NVIDIA Grace CPUs", "NVIDIA Grace")


def test_both_transformations_compose():
    # The real live case: "NVIDIA NeMo framework" and a bare "NeMo".
    assert _same("NVIDIA NeMo framework", "NeMo")


def test_case_and_surrounding_whitespace_do_not_fork_a_row():
    assert _same("  kubernetes ", "Kubernetes")


def test_quotes_and_trailing_punctuation_are_ignored():
    assert _same('"Kubernetes",', "Kubernetes")


# --- Merges that must NOT happen ---------------------------------------


def test_a_distinguishing_suffix_is_never_stripped():
    # The hazard that rules out containment matching. Both pairs are real
    # entries from the same live company record.
    assert not _same("NeMo", "NeMo Retriever")
    assert not _same("Quantum", "Quantum InfiniBand")


def test_docker_does_not_absorb_docker_swarm():
    # The canonical example of why containment matching is unsafe.
    assert not _same("Docker", "Docker Swarm", company="Acme")


def test_different_vendors_products_stay_distinct_within_one_company():
    """Only the company's *own* name is stripped, never a vendor list.

    A general vendor list would collapse "Google Cloud Storage" and "IBM
    Cloud Storage" into one row for any company that uses both.
    """
    assert not _same("Google Cloud Storage", "IBM Cloud Storage", company="Acme")
    assert not _same("AWS Lambda", "Azure Lambda", company="Acme")


def test_a_slash_separated_list_is_left_intact():
    # "Tesla/Hopper/Blackwell" names three products; splitting it would
    # invent observations that no extraction actually made.
    assert canonical_name("Tesla/Hopper/Blackwell", "NVIDIA") == "tesla/hopper/blackwell"


def test_only_one_trailing_descriptor_is_removed():
    # Stripping repeatedly could cascade a real name away.
    assert canonical_name("GPU Operator Platform", "NVIDIA") == "gpu operator"


def test_a_technology_named_only_the_company_survives():
    # Stripping would leave an empty key, which the caller skips - losing
    # the row entirely.
    assert canonical_name("NVIDIA", "NVIDIA") == "nvidia"


def test_a_generic_word_that_is_the_whole_name_survives():
    assert canonical_name("Platform", "Acme") == "platform"


def test_the_prefix_must_be_a_whole_leading_word():
    # "NVIDIAlike" is not an NVIDIA-prefixed product.
    assert canonical_name("NVIDIAlike", "NVIDIA") == "nvidialike"


# --- Edges -------------------------------------------------------------


def test_a_blank_name_yields_a_blank_key():
    assert canonical_name("", "NVIDIA") == ""
    assert canonical_name("   ", "NVIDIA") == ""


def test_no_company_name_still_normalises_case_and_spacing():
    assert canonical_name("  Kubernetes  ", None) == "kubernetes"


# --- Display name ------------------------------------------------------


def test_the_more_specific_spelling_is_shown():
    # "NVIDIA Omniverse" tells a reader who makes it; "Omniverse" does not.
    assert preferred_display_name("Omniverse", "NVIDIA Omniverse") == "NVIDIA Omniverse"


def test_a_shorter_later_spelling_does_not_replace_a_longer_one():
    assert preferred_display_name("NVIDIA Omniverse", "Omniverse") == "NVIDIA Omniverse"


def test_ties_keep_the_existing_name_so_the_page_does_not_reshuffle():
    assert preferred_display_name("Kubernetes", "kubernetes") == "Kubernetes"
