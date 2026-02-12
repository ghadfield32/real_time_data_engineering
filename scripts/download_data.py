"""Download NYC TLC Yellow Taxi trip data and reference files.

Usage:
    uv run python scripts/download_data.py

Downloads:
    - Yellow taxi trips parquet (Jan 2024, ~100MB)
    - Taxi zone lookup CSV (~10KB)
"""
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SEED_DIR = BASE_DIR / "nyc_taxi_dbt" / "seeds"

FILES = {
    "yellow_tripdata_2024-01.parquet": {
        "url": "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet",
        "dest": DATA_DIR,
    },
    "taxi_zone_lookup.csv": {
        "url": "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv",
        "dest": SEED_DIR,
    },
}


def download_file(name: str, url: str, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / name
    if dest_path.exists():
        print(f"  [skip] {dest_path} already exists")
        return
    print(f"  Downloading {name} from {url} ...")
    resp = requests.get(url, stream=True, timeout=300)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r  {pct:.1f}%", end="", flush=True)
    print(f"\n  Saved to {dest_path} ({dest_path.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    print("=== NYC Taxi Data Downloader ===\n")
    for name, info in FILES.items():
        download_file(name, info["url"], info["dest"])
    print("\nDone! Data is ready.")


if __name__ == "__main__":
    main()
