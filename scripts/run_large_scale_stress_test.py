"""Large-scale stress test script.

This script parses our massive datasets, runs the aetheriaforge coherence engine,
and generates massive evidences to test the Gradio app dashboard."""

from pathlib import Path
from time import perf_counter

import pandas as pd

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.orchestration.pipeline import ForgePipeline


def create_nyc_contract():
    return ForgeContract.from_dict({
        "dataset": {"name": "nyc_taxi", "version": "1.0.0"},
        "source": {"catalog": "public", "schema": "bronze", "table": "nyc"},
        "target": {"catalog": "public", "schema": "silver", "table": "nyc_forged"},
        "coherence": {"engine": "shannon", "thresholds": {"bronze_min": 0.5, "silver_min": 0.8, "gold_min": 0.95}},
        "schema_contract": {"enforce": False, "evolution": "versioned", "coerce_types": False},
        "resolution": {"enabled": False},
        "temporal": {"enabled": False}
    })

def create_covid_contract():
    return ForgeContract.from_dict({
        "dataset": {"name": "nyt_covid", "version": "1.0.0"},
        "source": {"catalog": "public", "schema": "bronze", "table": "covid"},
        "target": {"catalog": "public", "schema": "silver", "table": "covid_forged"},
        "coherence": {"engine": "shannon", "thresholds": {"bronze_min": 0.5, "silver_min": 0.8, "gold_min": 0.95}},
        "schema_contract": {"enforce": False, "evolution": "versioned", "coerce_types": False},
        "resolution": {"enabled": False},
        "temporal": {"enabled": False}
    })


def main():
    print("Loading NYC Parquet...")
    t0 = perf_counter()
    nyc_df = pd.read_parquet("data/raw/yellow_tripdata_2024-01.parquet")
    print(f"Loaded {len(nyc_df)} rows in {perf_counter() - t0:.2f}s")

    # Process NYC
    print("Running NYC Forge Pipeline...")
    evidence_dir = Path("output/stress-test/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    writer = EvidenceWriter(evidence_dir)

    pipeline = ForgePipeline(create_nyc_contract(), evidence_writer=writer)
    # We will simulate the transformation:
    # Let's say forged drops rows where passenger_count is NA, or some random drop.
    # To cause Some Coherence score loss.

    forged_nyc = nyc_df.dropna(subset=["passenger_count"]).reset_index(drop=True)

    t0 = perf_counter()
    res = pipeline.run(source_df=nyc_df, forged_df=forged_nyc, schema_columns=None, target_layer="silver")
    print(f"NYC Pipeline finished in {perf_counter() - t0:.2f}s with verdict: {res.pipeline_verdict}")

    print(r"\Loading Covid CSV...")
    t0 = perf_counter()
    covid_df = pd.read_csv("data/raw/us-counties.csv")
    print(f"Loaded {len(covid_df)} rows in {perf_counter() - t0:.2f}s")

    print("Running Covid Forge Pipeline...")
    pipeline_covid = ForgePipeline(create_covid_contract(), evidence_writer=writer)
    forged_covid = covid_df[covid_df["cases"] > 0].reset_index(drop=True)

    t0 = perf_counter()
    res2 = pipeline_covid.run(source_df=covid_df, forged_df=forged_covid, schema_columns=None, target_layer="silver")
    print(f"Covid Pipeline finished in {perf_counter() - t0:.2f}s with verdict: {res2.pipeline_verdict}")

if __name__ == "__main__":
    main()
