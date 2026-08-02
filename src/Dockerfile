FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

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
    PyYAML==6.0.2

COPY air_transport_statistics /app/air_transport_statistics

RUN mkdir -p /app/config /app/data /app/data_contracts /app/runtime

CMD ["python", "-m", "air_transport_statistics"]