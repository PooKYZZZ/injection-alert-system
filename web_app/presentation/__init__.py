# web_app/presentation/
#
# Layer: Presentation (Outermost delivery mechanism)
# Architectural Role: FastAPI routing, request/response serialization, middleware.
# This is the HTTP delivery adapter — it converts HTTP requests into application use case calls.
#
# Contents (to be implemented):
#   - app.py              : FastAPI application factory and startup lifecycle
#   - routers/            : endpoint definitions, grouped by domain concern
#   - middleware/         : rate limiting, audit logging, error normalization
#   - request_schemas.py  : Pydantic input models (HTTP boundary, not domain entities)
#   - response_schemas.py : Pydantic output models (HTTP boundary, not domain entities)
#
# Dependency Rule: imports from application/ (use cases) and infrastructure/ (DI bindings).
# Never imports directly from domain/ entities; communicate through application/ services.
