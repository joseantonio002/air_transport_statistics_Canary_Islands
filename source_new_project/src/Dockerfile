FROM python:3.12-slim

WORKDIR /opt/pipeline
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY data_contracts ./data_contracts
RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
# The pipeline command executes extract, validation, transform, load, and model_update.
CMD ["python", "-m", "pipeline", "run"]
