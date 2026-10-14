FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY alladin /app/alladin
COPY config.json /app/config.json
RUN useradd --uid 10001 --create-home lab && mkdir /app/data && chown lab:lab /app/data
USER lab
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=3).close()"
# HTTP binds loopback. For Linux deployment use host networking with a TLS reverse proxy.
CMD ["python", "-m", "alladin", "serve", "--paper-worker"]
