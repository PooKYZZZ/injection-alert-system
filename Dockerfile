FROM python@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

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
