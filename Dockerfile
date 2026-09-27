FROM apache/airflow:2.10.5-python3.12

USER airflow

COPY requirements-airflow.txt /requirements-airflow.txt

RUN pip install --no-cache-dir -r /requirements-airflow.txt
