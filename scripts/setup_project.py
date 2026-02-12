"""One-shot project bootstrap: copies profiles.yml.example to profiles.yml.

Usage:
    uv run python scripts/setup_project.py
"""
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DBT_DIR = BASE_DIR / "nyc_taxi_dbt"


def main() -> None:
    src = DBT_DIR / "profiles.yml.example"
    dst = DBT_DIR / "profiles.yml"

    if dst.exists():
        print(f"profiles.yml already exists at {dst}")
        return

    if not src.exists():
        print(f"ERROR: {src} not found")
        return

    shutil.copy2(src, dst)
    print(f"Created {dst} from example. Edit if needed, then run:")
    print(f"  cd nyc_taxi_dbt && uv run dbt debug --profiles-dir .")


if __name__ == "__main__":
    main()
