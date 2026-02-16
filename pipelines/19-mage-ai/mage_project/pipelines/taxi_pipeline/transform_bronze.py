"""
Transformer: Bronze layer - rename columns, cast types
"""
if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

@transformer
def transform_bronze(records, *args, **kwargs):
    """Rename columns from raw format to snake_case bronze format."""
    bronze = []
    for r in records:
        bronze.append({
            'vendor_id': int(r.get('VendorID', 0) or 0),
            'pickup_datetime': r.get('tpep_pickup_datetime', ''),
            'dropoff_datetime': r.get('tpep_dropoff_datetime', ''),
            'passenger_count': float(r.get('passenger_count', 0) or 0),
            'trip_distance': float(r.get('trip_distance', 0) or 0),
            'rate_code_id': int(r.get('RatecodeID', 0) or 0),
            'store_and_fwd_flag': r.get('store_and_fwd_flag', ''),
            'pickup_location_id': int(r.get('PULocationID', 0) or 0),
            'dropoff_location_id': int(r.get('DOLocationID', 0) or 0),
            'payment_type': int(r.get('payment_type', 0) or 0),
            'fare_amount': round(float(r.get('fare_amount', 0) or 0), 2),
            'extra': round(float(r.get('extra', 0) or 0), 2),
            'mta_tax': round(float(r.get('mta_tax', 0) or 0), 2),
            'tip_amount': round(float(r.get('tip_amount', 0) or 0), 2),
            'tolls_amount': round(float(r.get('tolls_amount', 0) or 0), 2),
            'improvement_surcharge': round(float(r.get('improvement_surcharge', 0) or 0), 2),
            'total_amount': round(float(r.get('total_amount', 0) or 0), 2),
            'congestion_surcharge': round(float(r.get('congestion_surcharge', 0) or 0), 2),
            'airport_fee': round(float(r.get('Airport_fee', 0) or 0), 2),
        })
    print(f"Bronze: {len(bronze)} records transformed")
    return bronze
