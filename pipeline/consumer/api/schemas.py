from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LoanApplication(BaseModel):
    loan_amnt: float = Field(..., description="The listed amount of the loan applied for by the borrower.", example=15000.0)
    funded_amnt: float = Field(..., description="The total amount committed to that loan at that point in time.", example=15000.0)
    term: int = Field(..., description="The number of payments on the loan in months.", example=36)
    int_rate: float = Field(..., description="Interest Rate on the loan.", example=10.99)
    installment: float = Field(..., description="The monthly payment owed by the borrower if the loan originates.", example=491.01)
    grade: str = Field(..., description="LC assigned loan grade.", example="B")
    sub_grade: str = Field(..., description="LC assigned loan subgrade.", example="B4")
    emp_length: int = Field(..., description="Employment length in years.", example=10)
    home_ownership: str = Field(..., description="The home ownership status provided by the borrower during registration.", example="MORTGAGE")
    annual_inc: float = Field(..., description="The self-reported annual income provided by the borrower during registration.", example=85000.0)
    verification_status: str = Field(..., description="Indicates if income was verified by LC, not verified, or if the income source was verified.", example="Verified")
    purpose: str = Field(..., description="A category provided by the borrower for the loan request.", example="debt_consolidation")
    dti: float = Field(..., description="A ratio calculated using the borrower’s total monthly debt payments on the total debt obligations.", example=15.2)
    delinq_2yrs: float = Field(..., description="The number of 30+ days past-due incidences of delinquency in the borrower's credit file for the past 2 years.", example=0.0)
    fico_range_low: float = Field(..., description="The lower boundary range the borrower’s FICO at loan origination belongs to.", example=700.0)
    fico_range_high: float = Field(..., description="The upper boundary range the borrower’s FICO at loan origination belongs to.", example=704.0)
    open_acc: float = Field(..., description="The number of open credit lines in the borrower's credit file.", example=14.0)
    pub_rec: float = Field(..., description="Number of derogatory public records.", example=0.0)
    revol_bal: float = Field(..., description="Total credit revolving balance.", example=12000.0)
    revol_util: float = Field(..., description="Revolving line utilization rate.", example=45.5)
    total_acc: float = Field(..., description="The total number of credit lines currently in the borrower's credit file.", example=28.0)
    initial_list_status: str = Field(..., description="The initial listing status of the loan.", example="w")
    application_type: str = Field(..., description="Indicates whether the loan is an individual application or a joint application.", example="Individual")


class LoanInflowEvent(LoanApplication):
    """Schema for loan applications as they flow through the Kafka pipeline."""
    application_id: str = Field(..., description="Unique UUID for the application")
    timestamp: datetime = Field(..., description="Timestamp of the application event")


class TopFactor(BaseModel):
    feature: str = Field(..., description="Name of the feature")
    impact: float = Field(..., description="Absolute impact on the prediction")
    direction: str = Field(..., description="Positive or Negative impact direction")


class PredictionResponse(BaseModel):
    prediction: int = Field(..., description="0 for Fully Paid, 1 for Charged Off")
    probability: float = Field(..., description="Probability of default")
    credit_score: int = Field(..., description="Basel scaled credit score (300-850)")
    risk_band: str = Field(..., description="Risk category (VERY_LOW to VERY_HIGH)")
    top_factors: List[TopFactor] = Field(..., description="Top factors influencing the prediction")
    model_version: str = Field(..., description="Version of the model used")
    prediction_timestamp: str = Field(..., description="ISO 8601 timestamp of prediction")


class BatchRequest(BaseModel):
    applications: List[LoanApplication] = Field(..., max_length=1000, description="List of loan applications to score in batch.")


class BatchResponse(BaseModel):
    predictions: List[PredictionResponse]
    batch_id: str = Field(..., description="Unique identifier for the batch")
    processing_time_ms: float = Field(..., description="Time taken to process the batch in ms")


class ModelInfo(BaseModel):
    version: str
    training_date: str
    auc_roc: float
    gini: float
    ks_statistic: float
    n_features: int
    feature_names: List[str]
