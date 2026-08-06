"""CloudEyes central ingestion platform."""

from .config import IngestionConfig
from .ingestion import IngestionPipeline
from .models import IngestionReceipt

__version__ = "0.1.0.dev0"

__all__ = ["IngestionConfig", "IngestionPipeline", "IngestionReceipt", "__version__"]
