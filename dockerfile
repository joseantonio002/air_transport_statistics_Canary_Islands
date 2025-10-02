ARG AIRFLOW_IMAGE=apache/airflow:3.1.0
FROM ${AIRFLOW_IMAGE}

USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt