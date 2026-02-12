# Capstone runtime v2 container
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app/src

RUN mkdir -p /app/outputs/spool

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --no-create-home appuser \
    && chown -R appuser:appuser /app/outputs

USER appuser

CMD ["python", "-m", "capruntime", "--config", "configs/runtime.yaml"]
