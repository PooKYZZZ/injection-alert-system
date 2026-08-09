FROM python@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY web_app ./web_app
COPY ml_model ./ml_model
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "--factory", "web_app.presentation.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
