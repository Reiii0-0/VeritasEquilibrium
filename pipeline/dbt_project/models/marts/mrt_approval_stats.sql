WITH features AS (
    SELECT * FROM {{ ref('int_loan_features') }}
),

minute_stats AS (
    SELECT
        DATE_TRUNC('minute', application_timestamp) AS calculation_date,
        COUNT(application_id) AS total_applications,
        SUM(is_approved) AS approved_applications,
        ROUND(AVG(is_approved) * 100, 2) AS approval_rate,
        SUM(loan_amount) AS total_loan_volume,
        AVG(interest_rate) AS avg_interest_rate,
        -- FAANG Metric: System Latency (Seconds)
        ROUND(AVG(EXTRACT(EPOCH FROM (ingested_at - application_timestamp))), 2) as avg_system_latency_sec
    FROM features
    GROUP BY 1
)

SELECT * FROM minute_stats
ORDER BY calculation_date DESC
