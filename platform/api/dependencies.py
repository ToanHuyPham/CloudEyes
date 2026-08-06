"""Compatibility exports for ingestion configuration and application state."""

from cloudeyes_platform.config import IngestionConfig
from cloudeyes_platform.server import TokenAuthenticator

__all__ = ["IngestionConfig", "TokenAuthenticator"]
