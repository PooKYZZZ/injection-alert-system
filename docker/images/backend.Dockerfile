FROM python@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG INSTALL_TRAINING_REQUIREMENTS=false

COPY requirements.txt requirements.train.txt ./
COPY pyproject.toml ./
RUN python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt
RUN if [ "$INSTALL_TRAINING_REQUIREMENTS" = "true" ]; then \
      python -m pip install --no-cache-dir -r requirements.train.txt; \
    fi

COPY alembic.ini ./
COPY migrations ./migrations
COPY web_app ./web_app
COPY ml_model ./ml_model
COPY scripts ./scripts

RUN groupadd --gid 10001 cybertrace \
    && useradd --no-log-init --uid 10001 --gid cybertrace --create-home \
      --home-dir /home/cybertrace --shell /usr/sbin/nologin cybertrace \
    && mkdir -p \
      runtime \
      ml_model/results/dashboard_retraining \
      ml_model/model_registry/archive \
      ml_model/model_registry/staging \
    && chown -R cybertrace:cybertrace \
      runtime \
      ml_model/results/dashboard_retraining \
      ml_model/model_registry/archive \
      ml_model/model_registry/staging

USER cybertrace

EXPOSE 8000

CMD ["uvicorn", "--factory", "web_app.presentation.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
