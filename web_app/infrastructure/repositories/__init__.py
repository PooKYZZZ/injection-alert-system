# web_app/infrastructure/repositories/
#
# Concrete repository implementations.
#
from web_app.infrastructure.repositories.traffic_log_repository import TrafficLogRepository
from web_app.infrastructure.repositories.enforcement_recommendation_repository import (
    EnforcementRecommendationRepository,
)

__all__ = ["TrafficLogRepository", "EnforcementRecommendationRepository"]
