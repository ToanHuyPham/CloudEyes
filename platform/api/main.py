"""Compatibility export for the implemented CloudEyes ingestion HTTP server."""

from cloudeyes_platform.server import IngestionApplication, create_server, handler_class

__all__ = ["IngestionApplication", "create_server", "handler_class"]
