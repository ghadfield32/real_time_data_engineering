"""
Python model: Anomaly detection on daily trip metrics.

Demonstrates dbt-duckdb's Python model support. Uses pandas to compute
z-scores and IQR-based outlier detection on daily trip counts and revenue,
identifying anomalous days (holidays, weather events, data issues).

Upstream: int_daily_summary
"""


def model(dbt, con):
    dbt.config(materialized="table", tags=["python"])

    # dbt.ref() returns a DuckDB relation; .df() converts to pandas DataFrame
    df = dbt.ref("int_daily_summary").df()

    # --- Z-score anomaly detection ---
    for col in ["total_trips", "total_revenue"]:
        mean = df[col].mean()
        std = df[col].std()
        df[f"{col}_z_score"] = ((df[col] - mean) / std).round(2)
        df[f"{col}_z_anomaly"] = df[f"{col}_z_score"].abs() > 2.0

    # --- IQR-based anomaly detection (robust to outliers) ---
    for col in ["total_trips", "total_revenue"]:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        df[f"{col}_iqr_anomaly"] = (df[col] < lower) | (df[col] > upper)

    # --- Composite anomaly flag (either method triggers) ---
    df["is_anomaly"] = (
        df["total_trips_z_anomaly"]
        | df["total_revenue_z_anomaly"]
        | df["total_trips_iqr_anomaly"]
        | df["total_revenue_iqr_anomaly"]
    )

    return df[
        [
            "pickup_date",
            "pickup_day_of_week",
            "is_weekend",
            "total_trips",
            "total_revenue",
            "total_trips_z_score",
            "total_revenue_z_score",
            "total_trips_z_anomaly",
            "total_revenue_z_anomaly",
            "total_trips_iqr_anomaly",
            "total_revenue_iqr_anomaly",
            "is_anomaly",
        ]
    ]
