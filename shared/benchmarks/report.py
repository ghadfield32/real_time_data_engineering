"""Generate comparison report from benchmark results.

Reads pipelines/comparison/results.csv and generates:
  - pipelines/comparison/comparison_report.md

Covers all 24 pipelines (P00-P23) across 11 tiers:
  Tier 1  : Core Pipelines (P00-P06)
  Tier 2  : Orchestration (P07-P09)
  Tier 3  : Serving Layer (P10)
  Tier 4  : Observability (P11)
  Tier 5  : CDC Pipelines (P12, P23)
  Tier 6  : Alternative Table Formats (P13, P22)
  Tier 7  : Alternative Streaming SQL (P14)
  Tier 8  : Lightweight Processors (P15, P20)
  Tier 9  : OLAP Engines (P16, P17)
  Tier 10 : Additional Orchestrators (P18, P19)
  Tier 11 : ML Feature Store (P21)

Cross-cutting comparisons:
  - Table Format: Iceberg vs Delta Lake vs Hudi
  - OLAP: ClickHouse vs Pinot vs Druid
  - All Orchestrators
  - Streaming SQL: RisingWave vs Materialize
  - Lightweight: Kafka Streams vs Bytewax
  - CDC: Debezium standalone vs Full Stack

Usage:
    python report.py
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COMPARISON_DIR = BASE_DIR / "pipelines" / "comparison"
CSV_PATH = COMPARISON_DIR / "results.csv"
REPORT_PATH = COMPARISON_DIR / "comparison_report.md"

# ----------------------------------------------------------------
# CSV column names (from results.csv)
# ----------------------------------------------------------------
COL_ID = "pipeline_id"
COL_NAME = "pipeline_name"
COL_INGESTION = "ingestion"
COL_PROCESSING = "processor"
COL_STORAGE = "storage"
COL_DBT_ADAPTER = "dbt_adapter"
COL_SERVICES = "containers"
COL_BRONZE = "bronze_rows"
COL_SILVER = "silver_rows"
COL_STATUS = "validation_status"
COL_STARTUP = "startup_s"
COL_RATE = "ingestion_s"
COL_BRONZE_S = "bronze_s"
COL_SILVER_S = "silver_s"
COL_TOTAL_S = "e2e_total_s"
COL_MEMORY = "memory_mb"
COL_NOTES = "notes"

# ----------------------------------------------------------------
# Pipeline-to-tier mapping
# ----------------------------------------------------------------
TIER_DEFS: list[dict] = [
    {
        "number": 1,
        "title": "Core Pipeline Comparison",
        "ids": [
            "00", "01", "02", "03", "04", "05", "06",
        ],
        "description": (
            "Pipelines P00-P06 form the core matrix "
            "comparing brokers (Kafka vs Redpanda) and "
            "processors (Flink vs Spark vs RisingWave)."
        ),
    },
    {
        "number": 2,
        "title": "Orchestration Comparison",
        "ids": ["07", "08", "09"],
        "description": (
            "Same Kafka+Flink+Iceberg data path, "
            "different orchestrators."
        ),
    },
    {
        "number": 3,
        "title": "Serving Layer",
        "ids": ["10"],
        "description": (
            "ClickHouse as the OLAP serving engine."
        ),
    },
    {
        "number": 4,
        "title": "Observability",
        "ids": ["11"],
        "description": (
            "Elementary + Soda Core data-quality "
            "observability stack."
        ),
    },
    {
        "number": 5,
        "title": "CDC Pipelines",
        "ids": ["12", "23"],
        "description": (
            "Change Data Capture pipelines: Debezium "
            "standalone (P12) and the Full Stack "
            "Capstone (P23)."
        ),
    },
    {
        "number": 6,
        "title": "Alternative Table Formats",
        "ids": ["13", "22"],
        "description": (
            "Delta Lake (P13) and Apache Hudi (P22) as "
            "alternatives to Apache Iceberg (P01/P02)."
        ),
    },
    {
        "number": 7,
        "title": "Alternative Streaming SQL",
        "ids": ["14"],
        "description": (
            "Materialize (P14) as an alternative to "
            "RisingWave (P03)."
        ),
    },
    {
        "number": 8,
        "title": "Lightweight Processors",
        "ids": ["15", "20"],
        "description": (
            "Kafka Streams (P15, Java) and Bytewax "
            "(P20, Python) -- lightweight, library-based "
            "stream processors with no separate cluster."
        ),
    },
    {
        "number": 9,
        "title": "OLAP Engines",
        "ids": ["16", "17"],
        "description": (
            "Apache Pinot (P16) and Apache Druid (P17) "
            "as alternatives to ClickHouse (P10)."
        ),
    },
    {
        "number": 10,
        "title": "Additional Orchestrators",
        "ids": ["18", "19"],
        "description": (
            "Prefect (P18) and Mage AI (P19) extend "
            "the orchestration comparison from Tier 2."
        ),
    },
    {
        "number": 11,
        "title": "ML Feature Store",
        "ids": ["21"],
        "description": (
            "Feast feature store (P21) -- materialises "
            "Iceberg features into an online store for "
            "ML serving."
        ),
    },
]

# Cross-cutting comparison definitions
CROSS_COMPARISONS: list[dict] = [
    {
        "title": (
            "Table Format Comparison: "
            "Iceberg vs Delta Lake vs Hudi"
        ),
        "ids": ["01", "13", "22"],
        "labels": {
            "01": "Iceberg (P01 Kafka+Flink)",
            "13": "Delta Lake (P13 Kafka+Spark)",
            "22": "Hudi (P22 Kafka+Spark)",
        },
        "notes": (
            "All three use Kafka for ingestion and write "
            "to MinIO object storage. Iceberg and Hudi use "
            "different table formats on the same Parquet "
            "base. Delta Lake uses its own log-based "
            "protocol."
        ),
    },
    {
        "title": (
            "OLAP Engine Comparison: "
            "ClickHouse vs Pinot vs Druid"
        ),
        "ids": ["10", "16", "17"],
        "labels": {
            "10": "ClickHouse (P10)",
            "16": "Apache Pinot (P16)",
            "17": "Apache Druid (P17)",
        },
        "notes": (
            "All three serve analytical queries over taxi "
            "data. ClickHouse is column-oriented SQL, Pinot "
            "is real-time OLAP with Kafka ingestion, Druid "
            "is time-series optimised with Kafka "
            "supervisors."
        ),
    },
    {
        "title": (
            "All Orchestrators: Kestra vs Airflow "
            "vs Dagster vs Prefect vs Mage"
        ),
        "ids": ["07", "08", "09", "18", "19"],
        "labels": {
            "07": "Kestra (P07)",
            "08": "Airflow (P08)",
            "09": "Dagster (P09)",
            "18": "Prefect (P18)",
            "19": "Mage AI (P19)",
        },
        "notes": (
            "All wrap the same Kafka+Flink+Iceberg data "
            "path (except Mage which uses its own "
            "block-based processing). Comparison focuses "
            "on overhead: memory, container count, startup, "
            "and E2E time."
        ),
    },
    {
        "title": (
            "Streaming SQL: RisingWave vs Materialize"
        ),
        "ids": ["03", "14"],
        "labels": {
            "03": "RisingWave (P03)",
            "14": "Materialize (P14)",
        },
        "notes": (
            "Both are PostgreSQL-wire-compatible streaming "
            "SQL engines that maintain materialised views "
            "over Kafka topics. RisingWave is Rust-based; "
            "Materialize is built on Timely Dataflow."
        ),
    },
    {
        "title": (
            "Lightweight Stream Processors: "
            "Kafka Streams vs Bytewax"
        ),
        "ids": ["15", "20"],
        "labels": {
            "15": "Kafka Streams (P15, Java)",
            "20": "Bytewax (P20, Python)",
        },
        "notes": (
            "Both are library-based processors that run "
            "inside the application JVM/Python process -- "
            "no separate cluster. Kafka Streams requires "
            "the JVM; Bytewax is pure Python."
        ),
    },
    {
        "title": (
            "CDC Comparison: Debezium Standalone "
            "vs Full Stack Capstone"
        ),
        "ids": ["12", "23"],
        "labels": {
            "12": "Debezium CDC (P12)",
            "23": "Full Stack Capstone (P23)",
        },
        "notes": (
            "P12 is standalone Debezium CDC (PostgreSQL "
            "WAL -> Kafka Connect -> Flink -> Iceberg). "
            "P23 extends it into a full stack capstone "
            "adding ClickHouse serving and Grafana "
            "dashboards."
        ),
    },
]


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def read_results() -> list[dict]:
    """Read pipeline benchmark results from CSV."""
    if not CSV_PATH.exists():
        print(f"No results found at {CSV_PATH}")
        print("Run benchmarks first: python runner.py --all")
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _lookup(
    results: list[dict], pid: str,
) -> Optional[dict]:
    """Return the result row for a pipeline_id, or None."""
    return next(
        (r for r in results if r.get(COL_ID) == pid),
        None,
    )


def _is_benchmarked(row: dict) -> bool:
    """True if the pipeline has been benchmarked (PASS)."""
    return row.get(COL_STATUS, "").upper() == "PASS"


def _is_numeric(value: Optional[str]) -> bool:
    """Return True if value is a parseable number."""
    if value is None:
        return False
    value = value.strip()
    if value in ("", "n/a", "auto", "N/A", "-"):
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _fmt(row: dict, col: str, fallback: str = "-") -> str:
    """Format a cell value for display."""
    raw = row.get(col, "")
    if _is_numeric(raw):
        return raw.strip() if raw else fallback
    return fallback


def _select(
    results: list[dict], ids: list[str],
) -> list[dict]:
    """Return rows matching pipeline IDs, preserving order."""
    id_set = set(ids)
    lookup = {
        r[COL_ID]: r
        for r in results
        if r.get(COL_ID) in id_set
    }
    return [lookup[pid] for pid in ids if pid in lookup]


def _partition_benchmarked(
    rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Split rows into (benchmarked, pending) lists."""
    benchmarked = [r for r in rows if _is_benchmarked(r)]
    pending = [r for r in rows if not _is_benchmarked(r)]
    return benchmarked, pending


def _pending_note(pending: list[dict]) -> list[str]:
    """Return markdown noting pending pipelines."""
    if not pending:
        return []
    names = ", ".join(
        f"P{r[COL_ID]} {r[COL_NAME]}" for r in pending
    )
    return [
        f"> **Pending benchmarks:** {names} "
        "(status READY -- run benchmarks to include "
        "in comparison)",
        "",
    ]


# ----------------------------------------------------------------
# Table builders
# ----------------------------------------------------------------

_FULL_COLS = [
    "Pipeline", "Ingestion", "Processing", "Storage",
    "Services", "Startup (s)", "Ingestion (evt/s)",
    "Bronze (s)", "Silver (s)", "Total Processing (s)",
    "Memory (MB)", "Status",
]
_FULL_TABLE_HEADER = "| " + " | ".join(_FULL_COLS) + " |"
_FULL_TABLE_SEP = "|" + "|".join(
    "-" * (len(c) + 2) for c in _FULL_COLS
) + "|"


def _full_table_row(r: dict) -> str:
    """Format a single full-detail table row."""
    status = "PASS" if _is_benchmarked(r) else "READY"
    cells = [
        f"P{r[COL_ID]} {r[COL_NAME][:28]}",
        r.get(COL_INGESTION, "-"),
        r.get(COL_PROCESSING, "-"),
        r.get(COL_STORAGE, "-"),
        _fmt(r, COL_SERVICES),
        _fmt(r, COL_STARTUP),
        _fmt(r, COL_RATE),
        _fmt(r, COL_BRONZE_S),
        _fmt(r, COL_SILVER_S),
        _fmt(r, COL_TOTAL_S),
        _fmt(r, COL_MEMORY),
        status,
    ]
    return "| " + " | ".join(cells) + " |"


_COMPACT_COLS = [
    "Pipeline", "Services", "Ingestion (evt/s)",
    "Total Processing (s)", "Memory (MB)", "Status",
    "Notes",
]
_COMPACT_HEADER = "| " + " | ".join(_COMPACT_COLS) + " |"
_COMPACT_SEP = "|" + "|".join(
    "-" * (len(c) + 2) for c in _COMPACT_COLS
) + "|"


def _compact_row(r: dict) -> str:
    """Format a single compact table row."""
    status = "PASS" if _is_benchmarked(r) else "READY"
    notes = r.get(COL_NOTES, "")
    if len(notes) > 50:
        notes = notes[:47] + "..."
    cells = [
        f"P{r[COL_ID]} {r[COL_NAME][:28]}",
        _fmt(r, COL_SERVICES),
        _fmt(r, COL_RATE),
        _fmt(r, COL_TOTAL_S),
        _fmt(r, COL_MEMORY),
        status,
        notes,
    ]
    return "| " + " | ".join(cells) + " |"


# ----------------------------------------------------------------
# Report sections
# ----------------------------------------------------------------

def _section_tier1(results: list[dict]) -> list[str]:
    """Generate Tier 1: Core Pipelines (P00-P06)."""
    ids = [f"{i:02d}" for i in range(7)]
    rows = _select(results, ids)
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append("## Tier 1: Core Pipeline Comparison")
    lines.append("")
    lines.append(
        "Pipelines P00-P06 form the core matrix comparing "
        "brokers (Kafka vs Redpanda) and processors "
        "(Flink vs Spark vs RisingWave)."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_FULL_TABLE_HEADER)
    lines.append(_FULL_TABLE_SEP)
    for r in rows:
        lines.append(_full_table_row(r))
    lines.append("")

    # --- Broker comparison ---
    lines.append("### Kafka vs Redpanda (Broker Comparison)")
    lines.append("")
    lines.append(
        "Holding processing + storage constant, "
        "only the broker differs:"
    )
    lines.append("")
    pairs = [
        ("01", "04", "Flink+Iceberg"),
        ("02", "05", "Spark+Iceberg"),
        ("03", "06", "RisingWave"),
    ]
    for kafka_id, rp_id, processor in pairs:
        k = _lookup(benchmarked, kafka_id)
        rp = _lookup(benchmarked, rp_id)
        if k and rp:
            lines.append(
                f"- **{processor}**: "
                f"Kafka {_fmt(k, COL_TOTAL_S)}s / "
                f"{_fmt(k, COL_MEMORY)}MB vs "
                f"Redpanda {_fmt(rp, COL_TOTAL_S)}s / "
                f"{_fmt(rp, COL_MEMORY)}MB"
            )
        else:
            missing = []
            if not k:
                missing.append(f"P{kafka_id}")
            if not rp:
                missing.append(f"P{rp_id}")
            lines.append(
                f"- **{processor}**: awaiting benchmarks "
                f"for {', '.join(missing)}"
            )
    lines.append("")

    # --- Processor comparison ---
    lines.append(
        "### Flink vs Spark vs RisingWave "
        "(Processor Comparison)"
    )
    lines.append("")
    lines.append(
        "Holding Kafka as broker, only the "
        "processor differs:"
    )
    lines.append("")
    procs = [
        ("01", "Flink"),
        ("02", "Spark"),
        ("03", "RisingWave"),
    ]
    for pid, name in procs:
        r = _lookup(benchmarked, pid)
        if r:
            lines.append(
                f"- **{name}** (P{pid}): "
                f"Total {_fmt(r, COL_TOTAL_S)}s, "
                f"Memory {_fmt(r, COL_MEMORY)}MB, "
                f"Rate {_fmt(r, COL_RATE)} evt/s"
            )
        else:
            lines.append(
                f"- **{name}** (P{pid}): "
                "awaiting benchmark"
            )
    lines.append("")
    return lines


def _section_tier2(results: list[dict]) -> list[str]:
    """Generate Tier 2: Orchestration (P07-P09)."""
    rows = _select(results, ["07", "08", "09"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 2: Orchestration Comparison "
        "(Kestra / Airflow / Dagster)"
    )
    lines.append("")
    lines.append(
        "Same Kafka+Flink+Iceberg data path, "
        "different orchestrators."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier3(results: list[dict]) -> list[str]:
    """Generate Tier 3: Serving Layer (P10)."""
    row = _lookup(results, "10")
    if not row:
        return []
    lines: list[str] = []
    lines.append("## Tier 3: Serving Layer (ClickHouse)")
    lines.append("")
    if _is_benchmarked(row):
        svc = row.get(COL_SERVICES, "-")
        note = row.get(COL_NOTES, "")
        lines.append(
            f"P10 {row[COL_NAME]}: {svc} services. "
            f"{note}"
        )
    else:
        lines.append(
            f"P10 {row[COL_NAME]}: "
            "**awaiting benchmark** (status READY)"
        )
    lines.append("")
    lines.append(
        "See `pipelines/10-serving-comparison/"
        "benchmark_results/` for detailed query "
        "latencies."
    )
    lines.append("")
    return lines


def _section_tier4(results: list[dict]) -> list[str]:
    """Generate Tier 4: Observability (P11)."""
    row = _lookup(results, "11")
    if not row:
        return []
    lines: list[str] = []
    lines.append(
        "## Tier 4: Observability "
        "(Elementary + Soda Core)"
    )
    lines.append("")
    if _is_benchmarked(row):
        svc = row.get(COL_SERVICES, "-")
        note = row.get(COL_NOTES, "")
        lines.append(
            f"P11 {row[COL_NAME]}: {svc} services. "
            f"{note}"
        )
    else:
        lines.append(
            f"P11 {row[COL_NAME]}: "
            "**awaiting benchmark** (status READY)"
        )
    lines.append("")
    lines.append(
        "See `pipelines/11-observability-stack/"
        "observability_results/` for quality reports."
    )
    lines.append("")
    return lines


def _section_tier5(results: list[dict]) -> list[str]:
    """Generate Tier 5: CDC Pipelines (P12, P23)."""
    rows = _select(results, ["12", "23"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 5: CDC Pipelines "
        "(Debezium / Full Stack Capstone)"
    )
    lines.append("")
    lines.append(
        "Change Data Capture pipelines: PostgreSQL WAL "
        "captured by Debezium and streamed through "
        "Kafka Connect."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier6(results: list[dict]) -> list[str]:
    """Generate Tier 6: Table Formats (P13, P22)."""
    rows = _select(results, ["13", "22"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 6: Alternative Table Formats "
        "(Delta Lake / Hudi)"
    )
    lines.append("")
    lines.append(
        "Delta Lake (P13) and Apache Hudi (P22) compared "
        "against Iceberg in Tier 1 (P01, P02)."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier7(results: list[dict]) -> list[str]:
    """Generate Tier 7: Streaming SQL (P14)."""
    row = _lookup(results, "14")
    if not row:
        return []
    lines: list[str] = []
    lines.append(
        "## Tier 7: Alternative Streaming SQL "
        "(Materialize)"
    )
    lines.append("")
    lines.append(
        "Materialize (P14) as an alternative to "
        "RisingWave (P03). Both are PG-wire-compatible "
        "streaming SQL engines."
    )
    lines.append("")
    if not _is_benchmarked(row):
        lines.extend(_pending_note([row]))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    lines.append(_compact_row(row))
    lines.append("")
    return lines


def _section_tier8(results: list[dict]) -> list[str]:
    """Generate Tier 8: Lightweight Processors (P15, P20)."""
    rows = _select(results, ["15", "20"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 8: Lightweight Stream Processors "
        "(Kafka Streams / Bytewax)"
    )
    lines.append("")
    lines.append(
        "Library-based processors with no separate "
        "cluster: Kafka Streams (P15, Java) and "
        "Bytewax (P20, Python)."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier9(results: list[dict]) -> list[str]:
    """Generate Tier 9: OLAP Engines (P16, P17)."""
    rows = _select(results, ["16", "17"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 9: OLAP Engines (Pinot / Druid)"
    )
    lines.append("")
    lines.append(
        "Apache Pinot (P16) and Apache Druid (P17) as "
        "alternatives to ClickHouse (P10)."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier10(results: list[dict]) -> list[str]:
    """Generate Tier 10: Orchestrators (P18, P19)."""
    rows = _select(results, ["18", "19"])
    if not rows:
        return []
    benchmarked, pending = _partition_benchmarked(rows)
    lines: list[str] = []
    lines.append(
        "## Tier 10: Additional Orchestrators "
        "(Prefect / Mage AI)"
    )
    lines.append("")
    lines.append(
        "Prefect (P18) and Mage AI (P19) extend the "
        "orchestration comparison from Tier 2."
    )
    lines.append("")
    lines.extend(_pending_note(pending))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    for r in rows:
        lines.append(_compact_row(r))
    lines.append("")
    return lines


def _section_tier11(results: list[dict]) -> list[str]:
    """Generate Tier 11: ML Feature Store (P21)."""
    row = _lookup(results, "21")
    if not row:
        return []
    lines: list[str] = []
    lines.append("## Tier 11: ML Feature Store (Feast)")
    lines.append("")
    lines.append(
        "Feast (P21) materialises Iceberg-based features "
        "into an online store for ML serving."
    )
    lines.append("")
    if not _is_benchmarked(row):
        lines.extend(_pending_note([row]))
    lines.append(_COMPACT_HEADER)
    lines.append(_COMPACT_SEP)
    lines.append(_compact_row(row))
    lines.append("")
    return lines


# ----------------------------------------------------------------
# Cross-cutting comparisons
# ----------------------------------------------------------------

def _cross_table_row(
    r: dict, label: str,
) -> str:
    """Format a cross-comparison table row."""
    status = "PASS" if _is_benchmarked(r) else "READY"
    notes = r.get(COL_NOTES, "")
    if len(notes) > 45:
        notes = notes[:42] + "..."
    cells = [
        f"{label} ({status})",
        _fmt(r, COL_SERVICES),
        _fmt(r, COL_RATE),
        _fmt(r, COL_TOTAL_S),
        _fmt(r, COL_MEMORY),
        r.get(COL_STORAGE, "-"),
        notes,
    ]
    return "| " + " | ".join(cells) + " |"


_CROSS_COLS = [
    "Pipeline", "Services", "Ingestion (evt/s)",
    "Total Processing (s)", "Memory (MB)", "Storage",
    "Notes",
]
_CROSS_HEADER = "| " + " | ".join(_CROSS_COLS) + " |"
_CROSS_SEP = "|" + "|".join(
    "-" * (len(c) + 2) for c in _CROSS_COLS
) + "|"


def _section_cross_comparisons(
    results: list[dict],
) -> list[str]:
    """Generate all cross-cutting comparison sections."""
    lines: list[str] = []
    lines.append("---")
    lines.append("")
    lines.append("# Cross-Cutting Comparisons")
    lines.append("")

    for comp in CROSS_COMPARISONS:
        rows = _select(results, comp["ids"])
        if not rows:
            continue

        benchmarked, pending = _partition_benchmarked(rows)

        lines.append(f"## {comp['title']}")
        lines.append("")
        lines.append(comp["notes"])
        lines.append("")
        lines.extend(_pending_note(pending))

        if benchmarked:
            lines.append(_CROSS_HEADER)
            lines.append(_CROSS_SEP)
            for r in rows:
                label = comp["labels"].get(
                    r[COL_ID], r[COL_NAME],
                )
                lines.append(_cross_table_row(r, label))
            lines.append("")
            lines.extend(
                _comparison_summary(
                    benchmarked, comp["labels"],
                )
            )
        else:
            lines.append(
                "*No benchmarked pipelines in this "
                "comparison yet. Run benchmarks to "
                "populate.*"
            )
            lines.append("")

    return lines


def _comparison_summary(
    benchmarked: list[dict],
    labels: dict[str, str],
) -> list[str]:
    """Produce a 'best in category' summary."""
    lines: list[str] = []
    if len(benchmarked) < 2:
        return lines

    def _label(r: dict) -> str:
        return labels.get(r[COL_ID], f"P{r[COL_ID]}")

    # Fastest total processing
    with_total = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_TOTAL_S, ""))
    ]
    if with_total:
        fastest = min(
            with_total,
            key=lambda r: float(r[COL_TOTAL_S]),
        )
        lines.append(
            f"- **Fastest processing**: "
            f"{_label(fastest)} "
            f"({fastest[COL_TOTAL_S]}s)"
        )

    # Lightest memory
    with_mem = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_MEMORY, ""))
    ]
    if with_mem:
        lightest = min(
            with_mem,
            key=lambda r: float(r[COL_MEMORY]),
        )
        lines.append(
            f"- **Lightest memory**: "
            f"{_label(lightest)} "
            f"({lightest[COL_MEMORY]}MB)"
        )

    # Fewest services
    with_svc = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_SERVICES, ""))
    ]
    if with_svc:
        simplest = min(
            with_svc,
            key=lambda r: int(r[COL_SERVICES]),
        )
        lines.append(
            f"- **Fewest services**: "
            f"{_label(simplest)} "
            f"({simplest[COL_SERVICES]} services)"
        )

    # Highest ingestion rate
    with_rate = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_RATE, ""))
    ]
    if with_rate:
        fastest_rate = max(
            with_rate,
            key=lambda r: float(r[COL_RATE]),
        )
        lines.append(
            f"- **Highest ingestion rate**: "
            f"{_label(fastest_rate)} "
            f"({fastest_rate[COL_RATE]} evt/s)"
        )

    lines.append("")
    return lines


# ----------------------------------------------------------------
# Recommendations
# ----------------------------------------------------------------

def _section_recommendations(
    results: list[dict],
) -> list[str]:
    """Generate overall recommendations."""
    benchmarked = [
        r for r in results if _is_benchmarked(r)
    ]
    pending = [
        r for r in results if not _is_benchmarked(r)
    ]
    if not benchmarked:
        return []

    lines: list[str] = []
    lines.append("---")
    lines.append("")
    lines.append("# Overall Recommendations")
    lines.append("")

    # Fastest total processing
    with_total = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_TOTAL_S, ""))
    ]
    if with_total:
        fastest = min(
            with_total,
            key=lambda r: float(r[COL_TOTAL_S]),
        )
        lines.append(
            f"- **Fastest E2E processing**: "
            f"P{fastest[COL_ID]} {fastest[COL_NAME]} "
            f"({fastest[COL_TOTAL_S]}s)"
        )

    # Lightest memory
    with_mem = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_MEMORY, ""))
    ]
    if with_mem:
        lightest = min(
            with_mem,
            key=lambda r: float(r[COL_MEMORY]),
        )
        lines.append(
            f"- **Lightest memory**: "
            f"P{lightest[COL_ID]} {lightest[COL_NAME]} "
            f"({lightest[COL_MEMORY]}MB)"
        )

    # Fewest services
    with_svc = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_SERVICES, ""))
    ]
    if with_svc:
        simplest = min(
            with_svc,
            key=lambda r: int(r[COL_SERVICES]),
        )
        lines.append(
            f"- **Simplest (fewest services)**: "
            f"P{simplest[COL_ID]} "
            f"{simplest[COL_NAME]} "
            f"({simplest[COL_SERVICES]} services)"
        )

    # Highest ingestion rate
    with_rate = [
        r for r in benchmarked
        if _is_numeric(r.get(COL_RATE, ""))
    ]
    if with_rate:
        fastest_rate = max(
            with_rate,
            key=lambda r: float(r[COL_RATE]),
        )
        lines.append(
            f"- **Highest ingestion rate**: "
            f"P{fastest_rate[COL_ID]} "
            f"{fastest_rate[COL_NAME]} "
            f"({fastest_rate[COL_RATE]} evt/s)"
        )

    lines.append("")

    # Coverage summary
    total = len(benchmarked) + len(pending)
    pct = 100 * len(benchmarked) // total if total else 0
    lines.append("### Benchmark Coverage")
    lines.append("")
    lines.append(
        f"- **Benchmarked**: {len(benchmarked)}/{total} "
        f"pipelines ({pct}%)"
    )
    if pending:
        lines.append(
            f"- **Pending**: {len(pending)} pipelines "
            "awaiting benchmarks:"
        )
        for r in pending:
            proc = r.get(COL_PROCESSING, "-")
            stor = r.get(COL_STORAGE, "-")
            lines.append(
                f"  - P{r[COL_ID]} {r[COL_NAME]} "
                f"({proc}, {stor})"
            )
    lines.append("")
    return lines


# ----------------------------------------------------------------
# Table of contents
# ----------------------------------------------------------------

_TOC_TIERS = [
    (
        "Tier 1: Core Pipelines (P00-P06)",
        "tier-1-core-pipeline-comparison",
    ),
    (
        "Tier 2: Orchestration (P07-P09)",
        "tier-2-orchestration-comparison-"
        "kestra--airflow--dagster",
    ),
    (
        "Tier 3: Serving Layer (P10)",
        "tier-3-serving-layer-clickhouse",
    ),
    (
        "Tier 4: Observability (P11)",
        "tier-4-observability-"
        "elementary--soda-core",
    ),
    (
        "Tier 5: CDC Pipelines (P12, P23)",
        "tier-5-cdc-pipelines-"
        "debezium--full-stack-capstone",
    ),
    (
        "Tier 6: Table Formats (P13, P22)",
        "tier-6-alternative-table-formats-"
        "delta-lake--hudi",
    ),
    (
        "Tier 7: Streaming SQL (P14)",
        "tier-7-alternative-streaming-sql-"
        "materialize",
    ),
    (
        "Tier 8: Lightweight (P15, P20)",
        "tier-8-lightweight-stream-processors-"
        "kafka-streams--bytewax",
    ),
    (
        "Tier 9: OLAP Engines (P16, P17)",
        "tier-9-olap-engines-pinot--druid",
    ),
    (
        "Tier 10: Orchestrators (P18, P19)",
        "tier-10-additional-orchestrators-"
        "prefect--mage-ai",
    ),
    (
        "Tier 11: ML Feature Store (P21)",
        "tier-11-ml-feature-store-feast",
    ),
]

_TOC_CROSS = [
    (
        "Table Format: Iceberg vs Delta Lake vs Hudi",
        "table-format-comparison-"
        "iceberg-vs-delta-lake-vs-hudi",
    ),
    (
        "OLAP: ClickHouse vs Pinot vs Druid",
        "olap-engine-comparison-"
        "clickhouse-vs-pinot-vs-druid",
    ),
    (
        "All Orchestrators",
        "all-orchestrators-kestra-vs-airflow-"
        "vs-dagster-vs-prefect-vs-mage",
    ),
    (
        "Streaming SQL: RisingWave vs Materialize",
        "streaming-sql-risingwave-vs-materialize",
    ),
    (
        "Lightweight: Kafka Streams vs Bytewax",
        "lightweight-stream-processors-"
        "kafka-streams-vs-bytewax",
    ),
    (
        "CDC: Debezium vs Full Stack",
        "cdc-comparison-debezium-standalone-"
        "vs-full-stack-capstone",
    ),
]


def _section_toc() -> list[str]:
    """Generate the table of contents."""
    lines: list[str] = []
    lines.append("## Table of Contents")
    lines.append("")
    lines.append("### Tiered Comparison")
    for title, anchor in _TOC_TIERS:
        lines.append(f"- [{title}](#{anchor})")
    lines.append("")
    lines.append("### Cross-Cutting Comparisons")
    for title, anchor in _TOC_CROSS:
        lines.append(f"- [{title}](#{anchor})")
    lines.append("")
    lines.append("### Summary")
    lines.append(
        "- [Overall Recommendations]"
        "(#overall-recommendations)"
    )
    lines.append("")
    return lines


# ----------------------------------------------------------------
# Master report generation
# ----------------------------------------------------------------

def generate_report(results: list[dict]) -> str:
    """Generate the full comparison report as Markdown."""
    lines: list[str] = []

    # Header
    lines.append("# Pipeline Comparison Report")
    lines.append("")
    lines.append(
        "Auto-generated from benchmark results "
        f"({len(results)} pipelines in results.csv)."
    )
    lines.append("")

    benchmarked_count = sum(
        1 for r in results if _is_benchmarked(r)
    )
    pending_count = len(results) - benchmarked_count
    lines.append(
        f"**Status**: {benchmarked_count} benchmarked "
        f"(PASS), {pending_count} pending (READY)"
    )
    lines.append("")

    # Table of contents
    lines.extend(_section_toc())

    # Tier sections
    lines.extend(_section_tier1(results))
    lines.extend(_section_tier2(results))
    lines.extend(_section_tier3(results))
    lines.extend(_section_tier4(results))
    lines.extend(_section_tier5(results))
    lines.extend(_section_tier6(results))
    lines.extend(_section_tier7(results))
    lines.extend(_section_tier8(results))
    lines.extend(_section_tier9(results))
    lines.extend(_section_tier10(results))
    lines.extend(_section_tier11(results))

    # Cross-cutting comparisons
    lines.extend(_section_cross_comparisons(results))

    # Recommendations
    lines.extend(_section_recommendations(results))

    return "\n".join(lines)


# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------

def main():
    """Generate and write the comparison report."""
    results = read_results()
    if not results:
        return

    report = generate_report(results)

    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    benchmarked = sum(
        1 for r in results if _is_benchmarked(r)
    )
    pending = len(results) - benchmarked
    print(f"Report written to: {REPORT_PATH}")
    print(
        f"Pipelines: {len(results)} total, "
        f"{benchmarked} benchmarked, {pending} pending"
    )


if __name__ == "__main__":
    main()
