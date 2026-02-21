#!/usr/bin/env python3
"""
render_sql.py — Strict template renderer for de_template.

Renders:
  flink/sql/*.sql.tmpl      → build/sql/*.sql
  flink/conf/core-site.xml  → build/conf/core-site.xml  (STORAGE-aware)

Selects active templates based on 4 axes (CATALOG, MODE, STORAGE).
Fails fast if any ${VAR} placeholder remains unsubstituted after rendering.

Usage (called by Makefile build-sql target):
    python3 scripts/render_sql.py
"""
import os
import pathlib
import re
import sys
from string import Template


def load_env(path=".env") -> dict:
    """Load .env file into a dict. Skips comments and blank lines."""
    env = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                # Strip inline comments: anything after whitespace+# is a comment
                v = re.sub(r'\s+#.*$', '', v)
                if k:
                    env[k] = v
    except FileNotFoundError:
        print(f"WARNING: {path} not found - using environment variables only")
    return env


def render_template(
    tmpl_path: pathlib.Path,
    env: dict,
    out_name: str,
    out_dir: pathlib.Path,
):
    """Render a single template file and write to out_dir/out_name."""
    raw = tmpl_path.read_text(encoding="utf-8")
    rendered = Template(raw).safe_substitute(env)

    # Strict check: fail if any ${VAR} placeholder was not substituted
    remaining = re.findall(r"\$\{(\w+)\}", rendered)
    if remaining:
        missing = sorted(set(remaining))
        sys.exit(
            f"\nERROR: Unsubstituted placeholders in {tmpl_path.name}:"
            f" {missing}\n"
            f"  Add these variables to your .env file.\n"
            f"  See .env.example for reference.\n"
        )

    out_path = out_dir / out_name
    out_path.write_text(rendered, encoding="utf-8")
    print(f"  rendered: {tmpl_path.name}  ->  {out_dir.name}/{out_name}")


def main():
    """Render all SQL and config templates based on axis variables."""
    # Load .env + override with actual environment variables (env wins)
    env = load_env(".env")
    env.update(os.environ)  # OS environment takes precedence

    catalog = env.get("CATALOG", "hadoop").strip().lower()
    mode = env.get("MODE", "batch").strip().lower()
    storage = env.get("STORAGE", "minio").strip().lower()

    sql_tmpl_dir = pathlib.Path("flink/sql")
    conf_tmpl_dir = pathlib.Path("flink/conf")
    sql_out_dir = pathlib.Path("build/sql")
    conf_out_dir = pathlib.Path("build/conf")
    sql_out_dir.mkdir(parents=True, exist_ok=True)
    conf_out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"\nRendering templates "
        f"(CATALOG={catalog}, MODE={mode}, STORAGE={storage})..."
    )

    # -----------------------------------------------------------------------
    # SQL templates → build/sql/
    # -----------------------------------------------------------------------

    # Active catalog template (hadoop vs rest)
    if catalog == "rest":
        catalog_tmpl = sql_tmpl_dir / "00_catalog_rest.sql.tmpl"
    else:
        catalog_tmpl = sql_tmpl_dir / "00_catalog.sql.tmpl"
    render_template(catalog_tmpl, env, "00_catalog.sql", sql_out_dir)

    # Source reference template (kept for backward compat; source DDL now
    # lives inside 05_bronze_batch.sql.tmpl for Flink session reliability)
    if mode == "streaming_bronze":
        source_tmpl = sql_tmpl_dir / "01_source_streaming.sql.tmpl"
    else:
        source_tmpl = sql_tmpl_dir / "01_source.sql.tmpl"
    if source_tmpl.exists():
        render_template(source_tmpl, env, "01_source.sql", sql_out_dir)

    # Fixed SQL templates (always rendered)
    #   05_bronze_batch.sql.tmpl  → batch Bronze
    #     (self-contained: SET + Kafka DDL + Bronze DDL + INSERT)
    #   06_silver.sql.tmpl        → Silver dedup + clean (batch)
    #   07_bronze_streaming.sql.tmpl → streaming Bronze (runs indefinitely)
    for tmpl_name, out_name in [
        ("05_bronze_batch.sql.tmpl",     "05_bronze_batch.sql"),
        ("06_silver.sql.tmpl",           "06_silver.sql"),
        ("07_bronze_streaming.sql.tmpl", "07_bronze_streaming.sql"),
    ]:
        tmpl_path = sql_tmpl_dir / tmpl_name
        if tmpl_path.exists():
            render_template(tmpl_path, env, out_name, sql_out_dir)
        else:
            print(f"  skipped (not found): {tmpl_name}")

    n_sql = len(list(sql_out_dir.glob("*.sql")))
    print(f"\n  SQL: {n_sql} files in build/sql/")

    # -----------------------------------------------------------------------
    # Hadoop core-site.xml → build/conf/core-site.xml  (STORAGE-aware)
    # -----------------------------------------------------------------------
    # STORAGE=minio  → core-site.minio.xml.tmpl
    #                  (explicit creds + custom endpoint)
    # STORAGE=aws_s3 → core-site.aws.xml.tmpl
    #                  (DefaultAWSCredentialsProviderChain, no endpoint)
    # STORAGE=gcs/azure → same aws template as baseline
    #                     (add connector JARs + env config manually)
    if storage == "minio":
        core_tmpl = conf_tmpl_dir / "core-site.minio.xml.tmpl"
    else:
        core_tmpl = conf_tmpl_dir / "core-site.aws.xml.tmpl"

    if core_tmpl.exists():
        render_template(core_tmpl, env, "core-site.xml", conf_out_dir)
    else:
        print(f"  skipped (not found): {core_tmpl.name}")

    print("\nAll templates rendered. build/conf/ and build/sql/ are ready.\n")


if __name__ == "__main__":
    main()
