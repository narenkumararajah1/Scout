"""External intelligence providers (V3 Enhancements Phase 7 -
docs/v3-enhancements/05_EXTERNAL_INTELLIGENCE.md,
docs/v3-enhancements/12_API_EVALUATIONS.md).

Every provider implements `base.ExternalProvider` and returns
`base.ExternalItem`, so the services that consume external intelligence
never name a vendor. See base.py for the attribution contract.
"""
