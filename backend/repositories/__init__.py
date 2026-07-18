"""Repository layer for Scout V2's core data model (docs/V2/DATA_MODEL.md).

Each module owns persistence for one entity (or a tightly-coupled pair,
e.g. Research Session + Signal). Repositories only read/write/update/delete
data - they perform no business analysis, per
docs/V2/IMPLEMENTATION_RULES.md's Repository Layer rule.
"""
