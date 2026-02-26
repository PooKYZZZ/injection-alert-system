# web_app/domain/
#
# Layer: Domain (Innermost)
# Architectural Role: Core business objects — entities, value objects, domain schemas.
# In Clean Architecture, this layer holds no dependencies on frameworks or infrastructure.
#
# Contents (to be implemented):
#   - RequestEntity       : represents a normalized HTTP request for WAF/ML triage
#   - AlertEntity         : audit-loggable security decision record
#   - InferenceResult     : value object: {label, confidence_score, threshold_gate}
#   - ThreatLevel         : domain enum: PASS | BLOCK | REVIEW
#
# Dependency Rule: This layer imports from NOTHING inside this project.
