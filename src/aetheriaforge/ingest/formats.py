"""File format detection and enumeration for the ingest module."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class FileFormat(Enum):
    """Supported file formats for ingestion."""

    CSV = "csv"
    TSV = "tsv"
    PARQUET = "parquet"
    JSON = "json"
    JSONL = "jsonl"
    EXCEL = "excel"
    XML = "xml"
    ORC = "orc"
    AVRO = "avro"
    FIXED_WIDTH = "fixed_width"


# Map file extensions to formats.  Extensions are lowercase without dot.
_EXTENSION_MAP: dict[str, FileFormat] = {
    "csv": FileFormat.CSV,
    "tsv": FileFormat.TSV,
    "tab": FileFormat.TSV,
    "parquet": FileFormat.PARQUET,
    "pq": FileFormat.PARQUET,
    "json": FileFormat.JSON,
    "jsonl": FileFormat.JSONL,
    "ndjson": FileFormat.JSONL,
    "xlsx": FileFormat.EXCEL,
    "xls": FileFormat.EXCEL,
    "xml": FileFormat.XML,
    "orc": FileFormat.ORC,
    "avro": FileFormat.AVRO,
    "txt": FileFormat.CSV,
    "dat": FileFormat.CSV,
    "fwf": FileFormat.FIXED_WIDTH,
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_EXTENSION_MAP)


def detect_format(path: Path) -> FileFormat:
    """Detect the file format from the file extension.

    Raises ``ValueError`` if the extension is not recognized.
    """
    ext = path.suffix.lstrip(".").lower()
    fmt = _EXTENSION_MAP.get(ext)
    if fmt is None:
        supported = ", ".join(sorted(f".{e}" for e in SUPPORTED_EXTENSIONS))
        msg = f"Unsupported file extension '.{ext}' for path '{path.name}'. Supported: {supported}"
        raise ValueError(msg)
    return fmt
