# web_app/presentation/schemas/
#
# Re-exports from the schemas module for clean import paths.
# Usage: from web_app.presentation.schemas import PredictionRequest, ...
#
from web_app.presentation.schemas.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse,
    HealthResponse,
)

__all__ = [
    "PredictionRequest",
    "PredictionResponse",
    "FeedbackRequest",
    "AlertResponse",
    "HealthResponse",
]
