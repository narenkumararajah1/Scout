"""A case study reaches Scout in two shapes and both must count as proof.

Curated CaseStudy entities are indexed with entity_type="case_study" and
no catalog category. Case studies uploaded to the Knowledge Library are
indexed as entity_type="document" with category="case_studies". The
enrichment pass that supplies proof points asked for both conditions
ANDed, which matches neither shape - so 81 uploaded case studies were
invisible to the one retrieval pass whose whole job is answering "where
have we done this before".
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.repositories import knowledge_repository


def _collection(count=10):
    fake = MagicMock()
    fake.count.return_value = count
    fake.query.return_value = {
        "documents": [["some content"]],
        "metadatas": [[{"entity_type": "document", "name": "A Case Study"}]],
        "distances": [[0.2]],
    }
    return fake


def _where_used(**kwargs):
    """Runs a search and returns the `where` clause it sent to Chroma."""
    fake = _collection()
    with patch.object(knowledge_repository, "get_knowledge_collection", return_value=fake):
        knowledge_repository.search_knowledge("q", **kwargs)
    return fake.query.call_args.kwargs["where"]


class TestFilterCombination:
    def test_two_filters_default_to_and(self):
        """Unchanged for every existing caller."""
        where = _where_used(entity_type="document", category="services")
        assert where == {"$and": [{"entity_type": "document"}, {"category": "services"}]}

    def test_match_any_switches_to_or(self):
        where = _where_used(entity_type="case_study", category="case_studies", match_any=True)
        assert where == {"$or": [{"entity_type": "case_study"}, {"category": "case_studies"}]}

    def test_a_single_filter_is_never_wrapped(self):
        """Chroma rejects $and/$or around one condition."""
        assert _where_used(entity_type="capability") == {"entity_type": "capability"}
        assert _where_used(entity_type="capability", match_any=True) == {"entity_type": "capability"}

    def test_no_filter_stays_none(self):
        assert _where_used() is None
        assert _where_used(match_any=True) is None


class TestEnrichmentAsksForBothShapes:
    def test_the_proof_point_pass_matches_either_representation(self):
        """The regression guard: this pass must not go back to AND.

        Asserted at the call site rather than through a live query,
        because the defect was in what enrichment *asked for*, not in
        how retrieval answered.
        """
        from backend.services import content_enrichment_service as enrichment

        with patch.object(enrichment, "retrieve_knowledge", return_value=[]) as retrieve:
            enrichment._retrieve_both("cloud migration", 4, 3)

        case_study_call = retrieve.call_args_list[1]
        assert case_study_call.args[2] == "case_study"
        assert case_study_call.args[3] == "case_studies"
        assert case_study_call.kwargs.get("match_any") is True

    def test_the_general_pass_is_still_unfiltered(self):
        """It must keep seeing the whole corpus, not just case studies."""
        from backend.services import content_enrichment_service as enrichment

        with patch.object(enrichment, "retrieve_knowledge", return_value=[]) as retrieve:
            enrichment._retrieve_both("cloud migration", 4, 3)

        general_call = retrieve.call_args_list[0]
        assert general_call.args[2] is None
        assert general_call.args[3] is None
