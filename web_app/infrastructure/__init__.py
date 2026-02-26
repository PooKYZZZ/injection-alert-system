# web_app/infrastructure/
#
# Layer: Infrastructure (Outermost implementation detail)
# Architectural Role: Concrete adapters — ORM models, database sessions, ML model loader,
# external WAF event reader. Implements interfaces defined in domain/.
#
# Contents (to be implemented):
#   - database.py         : SQLAlchemy engine, session factory, Base declarative model
#   - orm_models.py       : SQLAlchemy table mappings for AlertEntity persistence
#   - model_loader.py     : loads transformer model from model_registry/production/
#   - repositories/       : concrete implementations of domain repository interfaces
#
# Dependency Rule: imports from domain/ and application/ (implementing their abstractions).
# FastAPI, SQLAlchemy, and PyTorch are ONLY permitted here and in presentation/.
