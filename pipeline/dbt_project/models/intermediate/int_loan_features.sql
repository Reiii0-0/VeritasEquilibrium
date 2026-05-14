WITH staging AS (
    SELECT * FROM {{ ref('stg_loans') }}
),

enriched AS (
    SELECT
        *,
        CASE 
            WHEN interest_rate < 10.0 THEN 'Low Risk'
            WHEN interest_rate < 18.0 THEN 'Medium Risk'
            ELSE 'High Risk'
        END AS risk_category,
        CASE 
            WHEN interest_rate < 15.0 THEN 1 
            ELSE 0 
        END AS is_approved
    FROM staging
)

SELECT * FROM enriched
