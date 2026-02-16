"""
Transformer: Silver layer - quality filters, computed fields
"""
import hashlib
from datetime import datetime

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

@transformer
def transform_silver(bronze_records, *args, **kwargs):
    """Apply quality filters and compute derived fields."""
    silver = []
    for r in bronze_records:
        # Quality filters
        if not r.get('pickup_datetime') or not r.get('dropoff_datetime'):
            continue
        if r.get('trip_distance', 0) < 0 or r.get('fare_amount', 0) < 0:
            continue

        # Generate trip_id
        key = '|'.join([
            str(r['vendor_id']),
            str(r['pickup_datetime']),
            str(r['dropoff_datetime']),
            str(r['pickup_location_id']),
            str(r['dropoff_location_id']),
            str(r['fare_amount']),
            str(r['total_amount']),
        ])
        trip_id = hashlib.md5(key.encode()).hexdigest()

        # Compute duration
        try:
            pickup = datetime.fromisoformat(r['pickup_datetime'])
            dropoff = datetime.fromisoformat(r['dropoff_datetime'])
            duration_minutes = (dropoff - pickup).total_seconds() / 60
        except:
            duration_minutes = 0

        r['trip_id'] = trip_id
        r['trip_duration_minutes'] = round(duration_minutes, 2)
        silver.append(r)

    print(f"Silver: {len(silver)} records after quality filters")
    return silver
