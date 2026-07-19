"""Distribution Layer (V2 Phase 10, ARCHITECTURE.md).

Channel implementations that deliver a Report to a Recipient. Each
channel is independently callable and returns True/False for sent/skipped
or raises on a real send failure - backend.services.distribution_service
is the only caller, and decides how to record each outcome as Delivery
History.
"""
