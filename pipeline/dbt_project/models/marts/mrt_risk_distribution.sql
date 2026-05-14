WITH features AS (
    SELECT * FROM {{ ref('int_loan_features') }}
),

risk_stats AS (
    SELECT
        risk_category,
        COUNT(*) as app_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as share_percentage
    FROM features
    GROUP BY 1
)

SELECT * FROM risk_stats
ORDER BY share_percentage DESC
