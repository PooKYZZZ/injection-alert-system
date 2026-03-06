# web_app/domain/
#
# Layer: Domain (Innermost)
# Architectural Role: Core business objects — entities, value objects, domain interfaces.
# In Clean Architecture, this layer holds no dependencies on frameworks or infrastructure.
#
# Contents:
#   - interfaces.py          : TrafficLogEntity, ITrafficLogRepository
#   - (planned) enums.py     : ThreatLevel (PASS | BLOCK | REVIEW)
#
# Dependency Rule: This layer imports from NOTHING inside this project.
