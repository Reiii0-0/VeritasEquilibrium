import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import (
    BatchRequest,
    BatchResponse,
    LoanApplication,
    ModelInfo,
    PredictionResponse,
    TopFactor,
)
from src.models.scorecard import CreditScorecardModel

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# Global dict to hold our ML model
ml_models: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    model_path = os.getenv("MODEL_PATH", "artifacts/xgboost_scorecard_v1.joblib")
    logger.info(f"Loading model from {model_path}")
    try:
        model = CreditScorecardModel.load(model_path)
        ml_models["scorecard"] = model
        logger.info("Model loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load model at startup: {e}")
        ml_models["scorecard"] = None
    
    yield
    
    # Shutdown
    ml_models.clear()
    logger.info("Model unloaded.")


app = FastAPI(
    title="VeritasEquilibrium Credit Risk API",
    description="Real-Time Credit Risk Data Product scoring endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - Restricting origins for security
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def json_log_middleware(request: Request, call_next):
    """Structured JSON logging middleware."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    log_dict = {
        "method": request.method,
        "url": str(request.url),
        "status_code": response.status_code,
        "process_time_ms": round(process_time * 1000, 2),
    }
    logger.info(json.dumps(log_dict))
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom 422 error handler."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


def _score_dataframe(df: pd.DataFrame) -> list[PredictionResponse]:
    model: CreditScorecardModel = ml_models.get("scorecard")
    if not model or not model.is_fitted:
        raise RuntimeError("Model is not loaded or not fitted.")

    preds = model.predict(df)
    probas = model.predict_proba(df)[:, 1]
    scores = model.predict_score(df)
    bands = model.predict_risk_band(df)
    
    responses = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    for i in range(len(df)):
        # Mocking top factors for the API since SHAP processing per request can be heavy
        dummy_factors = [
            TopFactor(feature="dti", impact=0.15, direction="Negative"),
            TopFactor(feature="int_rate", impact=0.10, direction="Negative"),
        ]
        
        resp = PredictionResponse(
            prediction=int(preds[i]),
            probability=float(probas[i]),
            credit_score=int(scores[i]),
            risk_band=bands[i],
            top_factors=dummy_factors,
            model_version="v1.0.0",
            prediction_timestamp=now_iso,
        )
        responses.append(resp)
        
    return responses


@app.post("/predict", response_model=PredictionResponse)
async def predict(application: LoanApplication):
    """Scores a single loan application."""
    df = pd.DataFrame([application.model_dump()])
    
    try:
        responses = _score_dataframe(df)
        return responses[0]
    except RuntimeError as e:
        return JSONResponse(status_code=503, content={"detail": str(e)})
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.post("/predict/batch", response_model=BatchResponse)
async def predict_batch(request: BatchRequest):
    """Scores a batch of loan applications (max 1000)."""
    start_time = time.time()
    
    df = pd.DataFrame([app.model_dump() for app in request.applications])
    
    try:
        responses = _score_dataframe(df)
        process_time_ms = (time.time() - start_time) * 1000
        
        return BatchResponse(
            predictions=responses,
            batch_id=str(uuid.uuid4()),
            processing_time_ms=process_time_ms,
        )
    except RuntimeError as e:
        return JSONResponse(status_code=503, content={"detail": str(e)})
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/model/info", response_model=ModelInfo)
async def model_info():
    """Returns metadata about the currently loaded model."""
    model: CreditScorecardModel = ml_models.get("scorecard")
    if not model or not model.is_fitted:
        return JSONResponse(status_code=503, content={"detail": "Model not available"})
        
    features = getattr(model, "selected_features_", [])
    
    return ModelInfo(
        version="v1.0.0",
        training_date="2023-10-01",  # Static for prototype
        auc_roc=0.75,                # Placeholder, would read from MLflow/metadata
        gini=0.50,                   
        ks_statistic=0.40,
        n_features=len(features),
        feature_names=features,
    )


@app.get("/health")
async def health_check():
    """Healthcheck endpoint."""
    model = ml_models.get("scorecard")
    model_loaded = model is not None and getattr(model, "is_fitted", False)
    return {"status": "ok", "model_loaded": model_loaded}
