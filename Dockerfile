FROM otel/opentelemetry-collector-contrib:0.160.0@sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6 AS upstream
FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY clinic.py workload.py ./
COPY container/app.py container/app.py
RUN mkdir /data /queue && touch /app/readonly-probe && chown 10001:10001 /data /queue /app/readonly-probe
USER 10001:10001
CMD ["python", "container/app.py", "sink"]
FROM runtime AS collector
COPY --from=upstream /otelcol-contrib /usr/local/bin/otelcol-contrib
COPY container/collector.yaml /app/collector.yaml
CMD ["otelcol-contrib", "--config", "/app/collector.yaml"]
