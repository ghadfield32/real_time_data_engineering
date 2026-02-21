#!/bin/bash
# =============================================================================
# iceberg_maintenance.sh — Routine Iceberg table maintenance
# =============================================================================
# Called by: make compact-silver | expire-snapshots | vacuum | maintain
#
# Operations:
#   compact-silver:   Merge small Parquet files into 128MB files
#                     → Improves dbt and analytical query scan performance
#   expire-snapshots: Remove Iceberg snapshot history older than 7 days
#                     → Keeps MinIO storage clean; time-travel still works
#   vacuum:           Delete orphan data files not referenced by any snapshot
#                     → Recovers storage from failed writes / aborted jobs
#   maintain:         compact-silver + expire-snapshots together
# =============================================================================
set -e

OPERATION="${1:-help}"
SQL_CLIENT="${SQL_CLIENT:-docker compose exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded}"
CATALOG_SQL="build/sql/00_catalog.sql"

if [ ! -f "$CATALOG_SQL" ]; then
    echo "ERROR: $CATALOG_SQL not found. Run: make build-sql first."
    exit 1
fi

case "$OPERATION" in
  compact-silver)
    echo "=== Compacting Silver Iceberg table ==="
    echo "  Target file size: 128MB | Min threshold: 32MB"
    $SQL_CLIENT -i "$CATALOG_SQL" <<'EOF'
CALL iceberg_catalog.system.rewrite_data_files(
    table => 'silver.cleaned_trips',
    options => map['target-file-size-bytes', '134217728',
                   'min-file-size-threshold', '33554432']
);
EOF
    echo "Silver compaction complete."
    ;;

  expire-snapshots)
    echo "=== Expiring Iceberg snapshots older than 7 days ==="
    $SQL_CLIENT -i "$CATALOG_SQL" <<'EOF'
CALL iceberg_catalog.system.expire_snapshots(
    table => 'silver.cleaned_trips',
    older_than => TIMESTAMPADD(DAY, -7, NOW())
);
CALL iceberg_catalog.system.expire_snapshots(
    table => 'bronze.raw_trips',
    older_than => TIMESTAMPADD(DAY, -7, NOW())
);
EOF
    echo "Snapshot expiry complete."
    ;;

  vacuum)
    echo "=== Removing orphan Iceberg files ==="
    $SQL_CLIENT -i "$CATALOG_SQL" <<'EOF'
CALL iceberg_catalog.system.remove_orphan_files(
    table => 'silver.cleaned_trips',
    older_than => TIMESTAMPADD(DAY, -7, NOW())
);
CALL iceberg_catalog.system.remove_orphan_files(
    table => 'bronze.raw_trips',
    older_than => TIMESTAMPADD(DAY, -7, NOW())
);
EOF
    echo "Vacuum complete."
    ;;

  maintain)
    bash "$0" compact-silver
    bash "$0" expire-snapshots
    echo "Routine maintenance complete."
    ;;

  help|*)
    echo "Usage: $0 <operation>"
    echo "  compact-silver    — Merge small files to 128MB"
    echo "  expire-snapshots  — Remove snapshots older than 7 days"
    echo "  vacuum            — Delete orphan files"
    echo "  maintain          — compact + expire"
    ;;
esac
