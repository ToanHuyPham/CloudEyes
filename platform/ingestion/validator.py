"""Bundle verification remains authoritative at the ingestion boundary."""

from cloudeyes_agent.bundle.verification import BundleVerificationError, verify_bundle

__all__ = ["BundleVerificationError", "verify_bundle"]
