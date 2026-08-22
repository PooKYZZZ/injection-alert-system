# web_app/infrastructure/repositories/
#
# Concrete repository implementations. Keep imports lazy: the detached local
# retraining worker uses the filesystem repository without a database contract.
# API wiring still receives the same names through __getattr__ below.


def __getattr__(name: str):
    if name == "TrafficLogRepository":
        from web_app.infrastructure.repositories.traffic_log_repository import (
            TrafficLogRepository,
        )

        return TrafficLogRepository
    if name == "EnforcementRecommendationRepository":
        from web_app.infrastructure.repositories.enforcement_recommendation_repository import (
            EnforcementRecommendationRepository,
        )

        return EnforcementRecommendationRepository
    if name == "TrafficLabelReviewRepository":
        from web_app.infrastructure.repositories.traffic_label_review_repository import (
            TrafficLabelReviewRepository,
        )

        return TrafficLabelReviewRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "TrafficLogRepository",
    "EnforcementRecommendationRepository",
    "TrafficLabelReviewRepository",
]
