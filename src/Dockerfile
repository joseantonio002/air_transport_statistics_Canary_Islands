FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    duckdb==1.3.2 \
    pandas==2.3.3 \
    prophet==1.1.7 \
    cmdstanpy==1.2.5 \
    requests==2.32.4 \
    plotly==6.3.1 \
    python-dateutil==2.9.0.post0 \
    PyYAML==6.0.2

COPY src/air_transport_statistics /app/src/air_transport_statistics

RUN mkdir -p /app/docs /app/src/config /app/src/data /app/src/data_contracts /app/src/runtime

CMD ["python", "-m", "air_transport_statistics"]
