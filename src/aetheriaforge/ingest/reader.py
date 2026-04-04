"""File ingestion: read enterprise file formats into pandas DataFrames."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.ingest.formats import FileFormat, detect_format
from aetheriaforge.ingest.result import IngestResult


class FileIngestor:
    """Read files in common enterprise formats into DataFrames with evidence.

    Supports CSV, TSV, Parquet, JSON, JSONL, Excel, XML, ORC, Avro,
    and fixed-width text.  Format is detected from the file extension
    unless *file_format* is given explicitly.

    Optional dependencies per format:

    - **Excel:** ``openpyxl`` (``pip install openpyxl``)
    - **XML:** ``lxml`` (``pip install lxml``)
    - **Parquet / ORC:** ``pyarrow`` (``pip install pyarrow``)
    - **Avro:** ``fastavro`` (``pip install fastavro``)
    """

    def __init__(self, evidence_writer: EvidenceWriter | None = None) -> None:
        self.evidence_writer = evidence_writer

    def ingest(
        self,
        path: str | Path,
        *,
        file_format: FileFormat | str | None = None,
        options: dict[str, Any] | None = None,
    ) -> IngestResult:
        """Read a file and return an :class:`IngestResult`.

        Parameters
        ----------
        path:
            Path to the file to ingest.
        file_format:
            Override automatic format detection.  Accepts a
            :class:`FileFormat` member or its string value (e.g. ``"csv"``).
        options:
            Extra keyword arguments forwarded to the underlying pandas
            reader (e.g. ``{"delimiter": "|"}`` for CSV).
        """
        file_path = Path(path).resolve()
        opts: dict[str, Any] = dict(options) if options else {}

        if not file_path.is_file():
            return self._error_result(
                file_path, f"File not found: {file_path}", opts
            )

        # Resolve format
        fmt = self._resolve_format(file_path, file_format)
        if fmt is None:
            return self._error_result(
                file_path,
                f"Could not determine format for '{file_path.name}'",
                opts,
            )

        reader = _FORMAT_READERS.get(fmt)
        if reader is None:
            return self._error_result(
                file_path,
                f"No reader implemented for format '{fmt.value}'",
                opts,
            )

        try:
            df, warnings = reader(file_path, opts)
        except Exception as exc:  # noqa: BLE001
            return self._error_result(
                file_path,
                f"Read failed for {fmt.value}: {exc}",
                opts,
            )

        now_utc = datetime.now(tz=timezone.utc).isoformat()
        file_size = file_path.stat().st_size

        result = IngestResult(
            df=df,
            file_path=str(file_path),
            file_format=fmt,
            records_read=len(df),
            columns=list(df.columns),
            file_size_bytes=file_size,
            ingested_at=now_utc,
            warnings=warnings,
            options_applied=opts,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_format(
        file_path: Path,
        override: FileFormat | str | None,
    ) -> FileFormat | None:
        """Resolve the target format from an override or the file extension."""
        if override is not None:
            if isinstance(override, FileFormat):
                return override
            try:
                return FileFormat(override)
            except ValueError:
                return None
        try:
            return detect_format(file_path)
        except ValueError:
            return None

    def _error_result(
        self,
        file_path: Path,
        error: str,
        opts: dict[str, Any],
    ) -> IngestResult:
        """Build an IngestResult representing a failed ingestion."""
        now_utc = datetime.now(tz=timezone.utc).isoformat()
        try:
            file_size = file_path.stat().st_size
        except OSError:
            file_size = 0
        return IngestResult(
            df=pd.DataFrame(),
            file_path=str(file_path),
            file_format=FileFormat.CSV,  # default for error results
            records_read=0,
            columns=[],
            file_size_bytes=file_size,
            ingested_at=now_utc,
            errors=[error],
            options_applied=opts,
        )


# ======================================================================
# Format-specific readers
# ======================================================================
# Each reader returns (DataFrame, list-of-warnings).

_ReaderFn = type[None]  # used only for type alias readability


def _read_csv(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a CSV file."""
    return pd.read_csv(path, **opts), []


def _read_tsv(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a tab-separated file."""
    opts.setdefault("delimiter", "\t")
    return pd.read_csv(path, **opts), []


def _read_parquet(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a Parquet file (requires pyarrow)."""
    warnings: list[str] = []
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        warnings.append("pyarrow not installed; falling back to default pandas parquet engine")
    return pd.read_parquet(path, **opts), warnings


def _read_json(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a JSON file."""
    return pd.read_json(path, **opts), []


def _read_jsonl(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a JSON Lines file."""
    opts.setdefault("lines", True)
    return pd.read_json(path, **opts), []


def _read_excel(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read an Excel file (requires openpyxl)."""
    try:
        import openpyxl  # noqa: F401
    except ImportError as exc:
        msg = "openpyxl is required for Excel ingestion: pip install openpyxl"
        raise ImportError(msg) from exc
    return pd.read_excel(path, **opts), []


def _read_xml(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read an XML file (requires lxml)."""
    try:
        import lxml  # noqa: F401
    except ImportError as exc:
        msg = "lxml is required for XML ingestion: pip install lxml"
        raise ImportError(msg) from exc
    return pd.read_xml(path, **opts), []


def _read_orc(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read an ORC file (requires pyarrow)."""
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        msg = "pyarrow is required for ORC ingestion: pip install pyarrow"
        raise ImportError(msg) from exc
    return pd.read_orc(path, **opts), []


def _read_avro(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read an Avro file (requires fastavro)."""
    try:
        import fastavro
    except ImportError as exc:
        msg = "fastavro is required for Avro ingestion: pip install fastavro"
        raise ImportError(msg) from exc
    with open(path, "rb") as fh:
        reader = fastavro.reader(fh)
        records = list(reader)
    return pd.DataFrame(records, **opts), []


def _read_fixed_width(path: Path, opts: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Read a fixed-width text file."""
    return pd.read_fwf(path, **opts), []


_FORMAT_READERS: dict[
    FileFormat,
    Any,
] = {
    FileFormat.CSV: _read_csv,
    FileFormat.TSV: _read_tsv,
    FileFormat.PARQUET: _read_parquet,
    FileFormat.JSON: _read_json,
    FileFormat.JSONL: _read_jsonl,
    FileFormat.EXCEL: _read_excel,
    FileFormat.XML: _read_xml,
    FileFormat.ORC: _read_orc,
    FileFormat.AVRO: _read_avro,
    FileFormat.FIXED_WIDTH: _read_fixed_width,
}
