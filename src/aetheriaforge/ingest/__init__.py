"""File ingestion module — read enterprise file formats into DataFrames."""

from aetheriaforge.ingest.formats import FileFormat, detect_format
from aetheriaforge.ingest.reader import FileIngestor
from aetheriaforge.ingest.result import IngestResult

__all__ = [
    "FileFormat",
    "FileIngestor",
    "IngestResult",
    "detect_format",
]
