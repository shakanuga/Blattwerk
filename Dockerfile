FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/data

WORKDIR /app
COPY app/ /app/

RUN useradd -u 99 -g 100 -M -d /app blattwerk 2>/dev/null || true \
 && mkdir -p /data && chown 99:100 /data

USER 99:100
EXPOSE 8080
VOLUME ["/data"]

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/api/config',timeout=4)" || exit 1

CMD ["python", "server.py"]
