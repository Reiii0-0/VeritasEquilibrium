WITH source AS (
    SELECT * FROM {{ source('raw', 'loans') }}
),

renamed AS (
    SELECT
        application_id,
        timestamp AS application_timestamp,
        (payload->>'loan_amnt')::numeric AS loan_amount,
        (payload->>'int_rate')::numeric AS interest_rate,
        (payload->>'term')::varchar AS term,
        (payload->>'annual_inc')::numeric AS annual_income,
        (payload->>'purpose')::varchar AS purpose,
        (payload->>'home_ownership')::varchar AS home_ownership,
        (payload->>'emp_length')::varchar AS employment_length,
        (payload->>'dti')::numeric AS debt_to_income,
        (payload->>'delinq_2yrs')::integer AS delinq_2yrs,
        ingested_at
    FROM source
)

SELECT * FROM renamed
