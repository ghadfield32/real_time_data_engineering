from datetime import timedelta
from feast import Entity, Feature, FeatureView, FileSource, ValueType
from feast.types import Float64, Int64, String

# Entity
trip = Entity(
    name="trip_id",
    value_type=ValueType.STRING,
    description="Unique taxi trip identifier",
)

pickup_location = Entity(
    name="pickup_location_id",
    value_type=ValueType.INT64,
    description="Pickup taxi zone ID",
)

# File source (parquet from Iceberg Silver layer)
trip_source = FileSource(
    path="/app/feast_repo/data/silver_trips.parquet",
    timestamp_field="pickup_datetime",
)

# Feature View: Trip features for ML
trip_features = FeatureView(
    name="trip_features",
    entities=[trip],
    ttl=timedelta(days=365),
    schema=[
        Feature(name="vendor_id", dtype=Int64),
        Feature(name="passenger_count", dtype=Float64),
        Feature(name="trip_distance", dtype=Float64),
        Feature(name="fare_amount", dtype=Float64),
        Feature(name="tip_amount", dtype=Float64),
        Feature(name="total_amount", dtype=Float64),
        Feature(name="payment_type", dtype=Int64),
        Feature(name="pickup_location_id", dtype=Int64),
        Feature(name="dropoff_location_id", dtype=Int64),
    ],
    source=trip_source,
    online=True,
)

# Feature View: Location aggregation features
location_source = FileSource(
    path="/app/feast_repo/data/location_features.parquet",
    timestamp_field="feature_timestamp",
)

location_features = FeatureView(
    name="location_features",
    entities=[pickup_location],
    ttl=timedelta(days=365),
    schema=[
        Feature(name="avg_fare", dtype=Float64),
        Feature(name="avg_trip_distance", dtype=Float64),
        Feature(name="avg_tip_percentage", dtype=Float64),
        Feature(name="trip_count", dtype=Int64),
    ],
    source=location_source,
    online=True,
)
