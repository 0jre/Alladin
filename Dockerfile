FROM python:3.12-slim
WORKDIR /app
COPY alladin /app/alladin
COPY config.json /app/config.json
RUN useradd --uid 10001 --create-home lab && mkdir /app/data && chown lab:lab /app/data
USER lab
# HTTP binds loopback. For Linux deployment use host networking with a TLS reverse proxy.
CMD ["python", "-m", "alladin", "serve"]
