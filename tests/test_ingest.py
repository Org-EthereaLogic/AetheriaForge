"""Tests for the ingest module — file format detection, reading, and evidence.

Exercises CSV, TSV, JSON, JSONL, Parquet, Excel, XML, ORC, Avro, and
fixed-width ingestion.  Each test creates a temporary file on disk and
reads it back through the FileIngestor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.ingest import FileFormat, FileIngestor, IngestResult, detect_format

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Carol"],
        "score": [0.91, 0.85, 0.77],
    })


@pytest.fixture()
def evidence_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evidence"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

class TestDetectFormat:
    def test_csv(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.csv") == FileFormat.CSV

    def test_tsv(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.tsv") == FileFormat.TSV

    def test_tab(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.tab") == FileFormat.TSV

    def test_parquet(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.parquet") == FileFormat.PARQUET

    def test_pq(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.pq") == FileFormat.PARQUET

    def test_json(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.json") == FileFormat.JSON

    def test_jsonl(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.jsonl") == FileFormat.JSONL

    def test_ndjson(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.ndjson") == FileFormat.JSONL

    def test_xlsx(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.xlsx") == FileFormat.EXCEL

    def test_xls(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.xls") == FileFormat.EXCEL

    def test_xml(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.xml") == FileFormat.XML

    def test_orc(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.orc") == FileFormat.ORC

    def test_avro(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.avro") == FileFormat.AVRO

    def test_fwf(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.fwf") == FileFormat.FIXED_WIDTH

    def test_txt_defaults_csv(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.txt") == FileFormat.CSV

    def test_dat_defaults_csv(self, tmp_path: Path) -> None:
        assert detect_format(tmp_path / "data.dat") == FileFormat.CSV

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported file extension"):
            detect_format(tmp_path / "data.pickle")


# ---------------------------------------------------------------------------
# CSV ingestion
# ---------------------------------------------------------------------------

class TestCSVIngestion:
    def test_basic_csv(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        result = FileIngestor().ingest(csv_path)

        assert result.ok
        assert result.records_read == 3
        assert result.file_format == FileFormat.CSV
        assert result.columns == ["id", "name", "score"]
        assert result.file_size_bytes > 0
        pd.testing.assert_frame_equal(result.df, sample_df)

    def test_csv_with_delimiter_option(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        pipe_path = tmp_path / "data.csv"
        sample_df.to_csv(pipe_path, index=False, sep="|")
        result = FileIngestor().ingest(pipe_path, options={"delimiter": "|"})

        assert result.ok
        assert result.records_read == 3

    def test_csv_with_encoding(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({"city": ["Munchen", "Zurich"]})
        df.to_csv(csv_path, index=False, encoding="utf-8")
        result = FileIngestor().ingest(csv_path, options={"encoding": "utf-8"})
        assert result.ok

    def test_txt_treated_as_csv(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        txt_path = tmp_path / "data.txt"
        sample_df.to_csv(txt_path, index=False)
        result = FileIngestor().ingest(txt_path)

        assert result.ok
        assert result.file_format == FileFormat.CSV

    def test_empty_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("id,name,score\n")
        result = FileIngestor().ingest(csv_path)
        assert result.ok
        assert result.records_read == 0
        assert result.columns == ["id", "name", "score"]


# ---------------------------------------------------------------------------
# TSV ingestion
# ---------------------------------------------------------------------------

class TestTSVIngestion:
    def test_basic_tsv(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        tsv_path = tmp_path / "data.tsv"
        sample_df.to_csv(tsv_path, index=False, sep="\t")
        result = FileIngestor().ingest(tsv_path)

        assert result.ok
        assert result.file_format == FileFormat.TSV
        assert result.records_read == 3
        pd.testing.assert_frame_equal(result.df, sample_df)


# ---------------------------------------------------------------------------
# Parquet ingestion
# ---------------------------------------------------------------------------

class TestParquetIngestion:
    def test_basic_parquet(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        pq_path = tmp_path / "data.parquet"
        sample_df.to_parquet(pq_path, index=False)
        result = FileIngestor().ingest(pq_path)

        assert result.ok
        assert result.file_format == FileFormat.PARQUET
        assert result.records_read == 3
        pd.testing.assert_frame_equal(result.df, sample_df)


# ---------------------------------------------------------------------------
# JSON ingestion
# ---------------------------------------------------------------------------

class TestJSONIngestion:
    def test_basic_json(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        json_path = tmp_path / "data.json"
        sample_df.to_json(json_path, orient="records")
        result = FileIngestor().ingest(json_path)

        assert result.ok
        assert result.file_format == FileFormat.JSON
        assert result.records_read == 3

    def test_jsonl(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        jsonl_path = tmp_path / "data.jsonl"
        sample_df.to_json(jsonl_path, orient="records", lines=True)
        result = FileIngestor().ingest(jsonl_path)

        assert result.ok
        assert result.file_format == FileFormat.JSONL
        assert result.records_read == 3

    def test_ndjson(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        ndjson_path = tmp_path / "data.ndjson"
        sample_df.to_json(ndjson_path, orient="records", lines=True)
        result = FileIngestor().ingest(ndjson_path)

        assert result.ok
        assert result.file_format == FileFormat.JSONL


# ---------------------------------------------------------------------------
# Excel ingestion
# ---------------------------------------------------------------------------

class TestExcelIngestion:
    def test_basic_xlsx(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        xlsx_path = tmp_path / "data.xlsx"
        sample_df.to_excel(xlsx_path, index=False)
        result = FileIngestor().ingest(xlsx_path)

        assert result.ok
        assert result.file_format == FileFormat.EXCEL
        assert result.records_read == 3
        pd.testing.assert_frame_equal(result.df, sample_df)

    def test_excel_with_sheet_name(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        xlsx_path = tmp_path / "data.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            sample_df.to_excel(writer, sheet_name="MySheet", index=False)
        result = FileIngestor().ingest(xlsx_path, options={"sheet_name": "MySheet"})

        assert result.ok
        assert result.records_read == 3


# ---------------------------------------------------------------------------
# XML ingestion
# ---------------------------------------------------------------------------

class TestXMLIngestion:
    def test_basic_xml(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "data.xml"
        xml_content = (
            "<?xml version='1.0' encoding='utf-8'?>\n"
            "<data>\n"
            "  <row><id>1</id><name>Alice</name></row>\n"
            "  <row><id>2</id><name>Bob</name></row>\n"
            "</data>"
        )
        xml_path.write_text(xml_content)
        result = FileIngestor().ingest(xml_path)

        assert result.ok
        assert result.file_format == FileFormat.XML
        assert result.records_read == 2
        assert "id" in result.columns
        assert "name" in result.columns


# ---------------------------------------------------------------------------
# ORC ingestion
# ---------------------------------------------------------------------------

class TestORCIngestion:
    def test_basic_orc(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        import pyarrow as pa
        import pyarrow.orc as orc

        orc_path = tmp_path / "data.orc"
        table = pa.Table.from_pandas(sample_df)
        orc.write_table(table, str(orc_path))

        result = FileIngestor().ingest(orc_path)

        assert result.ok
        assert result.file_format == FileFormat.ORC
        assert result.records_read == 3


# ---------------------------------------------------------------------------
# Avro ingestion
# ---------------------------------------------------------------------------

class TestAvroIngestion:
    def test_basic_avro(self, tmp_path: Path) -> None:
        import fastavro

        avro_path = tmp_path / "data.avro"
        schema = {
            "type": "record",
            "name": "Test",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        with open(avro_path, "wb") as fh:
            fastavro.writer(fh, schema, records)

        result = FileIngestor().ingest(avro_path)

        assert result.ok
        assert result.file_format == FileFormat.AVRO
        assert result.records_read == 2
        assert "id" in result.columns
        assert "name" in result.columns


# ---------------------------------------------------------------------------
# Fixed-width ingestion
# ---------------------------------------------------------------------------

class TestFixedWidthIngestion:
    def test_basic_fwf(self, tmp_path: Path) -> None:
        fwf_path = tmp_path / "data.fwf"
        fwf_path.write_text(
            "id    name   score\n"
            "1     Alice  0.91 \n"
            "2     Bob    0.85 \n"
        )
        result = FileIngestor().ingest(fwf_path)

        assert result.ok
        assert result.file_format == FileFormat.FIXED_WIDTH
        assert result.records_read == 2


# ---------------------------------------------------------------------------
# Format override
# ---------------------------------------------------------------------------

class TestFormatOverride:
    def test_string_override(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        dat_path = tmp_path / "data.dat"
        sample_df.to_csv(dat_path, index=False, sep="\t")
        result = FileIngestor().ingest(dat_path, file_format="tsv")

        assert result.ok
        assert result.file_format == FileFormat.TSV
        assert result.records_read == 3

    def test_enum_override(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        txt_path = tmp_path / "data.txt"
        sample_df.to_csv(txt_path, index=False, sep="\t")
        result = FileIngestor().ingest(txt_path, file_format=FileFormat.TSV)

        assert result.ok
        assert result.file_format == FileFormat.TSV


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_file_not_found(self, tmp_path: Path) -> None:
        result = FileIngestor().ingest(tmp_path / "nonexistent.csv")
        assert not result.ok
        assert "File not found" in result.errors[0]

    def test_malformed_csv(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "bad.csv"
        # Write binary garbage that isn't valid CSV
        bad_path.write_bytes(b"\x00\x01\x02\x80\x81\x82")
        result = FileIngestor().ingest(bad_path)
        # Should either error or return something — either way, no crash
        assert isinstance(result, IngestResult)

    def test_invalid_format_override(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        result = FileIngestor().ingest(csv_path, file_format="not_a_format")
        assert not result.ok
        assert "Could not determine format" in result.errors[0]

    def test_unsupported_extension_file(self, tmp_path: Path) -> None:
        weird = tmp_path / "data.pickle"
        weird.write_text("not relevant")
        result = FileIngestor().ingest(weird)
        assert not result.ok


# ---------------------------------------------------------------------------
# Evidence writing
# ---------------------------------------------------------------------------

class TestEvidenceWriting:
    def test_evidence_written_on_success(
        self, tmp_path: Path, evidence_dir: Path, sample_df: pd.DataFrame
    ) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        writer = EvidenceWriter(evidence_dir)
        ingestor = FileIngestor(evidence_writer=writer)
        result = ingestor.ingest(csv_path)

        assert result.ok
        assert result.evidence_path is not None
        evidence = json.loads(Path(result.evidence_path).read_text())
        assert evidence["event"] == "ingest_result"
        assert evidence["records_read"] == 3
        assert evidence["file_format"] == "csv"

    def test_no_evidence_without_writer(
        self, tmp_path: Path, sample_df: pd.DataFrame
    ) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        result = FileIngestor().ingest(csv_path)

        assert result.ok
        assert result.evidence_path is None


# ---------------------------------------------------------------------------
# IngestResult API
# ---------------------------------------------------------------------------

class TestIngestResultAPI:
    def test_as_dict_roundtrip(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        result = FileIngestor().ingest(csv_path)
        d = result.as_dict()

        assert d["event"] == "ingest_result"
        assert d["file_format"] == "csv"
        assert d["records_read"] == 3
        assert isinstance(d["columns"], list)
        # Verify JSON-serializable
        json.dumps(d)

    def test_ok_true_on_success(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        csv_path = tmp_path / "data.csv"
        sample_df.to_csv(csv_path, index=False)
        result = FileIngestor().ingest(csv_path)
        assert result.ok is True

    def test_ok_false_on_error(self, tmp_path: Path) -> None:
        result = FileIngestor().ingest(tmp_path / "ghost.csv")
        assert result.ok is False
