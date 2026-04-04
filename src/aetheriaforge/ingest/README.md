# ingest/

File ingestion module — reads enterprise file formats into pandas DataFrames
with optional evidence writing.

## Supported Formats

| Format | Extensions | Required Dependency |
| --- | --- | --- |
| CSV | `.csv`, `.txt`, `.dat` | _(none — pandas built-in)_ |
| TSV | `.tsv`, `.tab` | _(none — pandas built-in)_ |
| Parquet | `.parquet`, `.pq` | `pyarrow` |
| JSON | `.json` | _(none — pandas built-in)_ |
| JSON Lines | `.jsonl`, `.ndjson` | _(none — pandas built-in)_ |
| Excel | `.xlsx`, `.xls` | `openpyxl` |
| XML | `.xml` | `lxml` |
| ORC | `.orc` | `pyarrow` |
| Avro | `.avro` | `fastavro` |
| Fixed-width | `.fwf` | _(none — pandas built-in)_ |

Install all optional readers at once:

```bash
uv sync --group ingest
```

## Usage

```python
from aetheriaforge.ingest import FileIngestor

ingestor = FileIngestor()
result = ingestor.ingest("data.parquet")

if result.ok:
    df = result.df  # pandas DataFrame
    print(f"Read {result.records_read} records, {len(result.columns)} columns")
else:
    print(result.errors)
```

Format is detected from the file extension. Override with `file_format=`:

```python
result = ingestor.ingest("data.dat", file_format="tsv")
```

Pass reader-specific options through `options=`:

```python
result = ingestor.ingest("data.csv", options={"delimiter": "|", "encoding": "latin-1"})
result = ingestor.ingest("data.xlsx", options={"sheet_name": "Q1 Report"})
```

## Evidence

When constructed with an `EvidenceWriter`, the ingestor writes an ingestion
artifact for every file read:

```python
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.ingest import FileIngestor

writer = EvidenceWriter(Path("/tmp/evidence"))
ingestor = FileIngestor(evidence_writer=writer)
result = ingestor.ingest("data.csv")
# result.evidence_path → path to the JSON artifact
```

## Module Contents

| File | Purpose |
| --- | --- |
| `formats.py` | `FileFormat` enum, extension mapping, `detect_format()` |
| `result.py` | `IngestResult` dataclass with `as_dict()` for evidence |
| `reader.py` | `FileIngestor` class with format-specific readers |
