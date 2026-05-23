# Dockerfile — Dispatch Backend
# Multi-stage build with kimi-cli vendored in.

FROM python:3.13-slim AS kimi-base
RUN pip install --no-cache-dir kimi-cli==1.43.0

FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=kimi-base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=kimi-base /usr/local/bin/kimi /usr/local/bin/kimi

WORKDIR /app
COPY core /app/core
COPY dispatch /app/dispatch
COPY dispatch/skills /app/skills
RUN pip install --no-cache-dir -r /app/dispatch/requirements.txt

ENV PYTHONPATH=/app
ENV HOME=/home/dispatch
ENV KIMI_CONFIG_DIR=/home/dispatch/.kimi

RUN useradd -u 1000 -m dispatch && \
    chown -R dispatch /home/dispatch /app && \
    chmod +x /app/dispatch/entrypoint.sh

RUN mkdir -p /home/dispatch && \
    printf '[safe]\n\tdirectory = *\n' > /home/dispatch/.gitconfig && \
    chown dispatch:dispatch /home/dispatch/.gitconfig

USER dispatch
EXPOSE 10060
ENTRYPOINT ["/app/dispatch/entrypoint.sh"]
