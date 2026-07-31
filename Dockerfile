FROM python@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY web_app ./web_app
COPY ml_model ./ml_model
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "--factory", "web_app.presentation.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
