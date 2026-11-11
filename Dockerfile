FROM honeygain/honeygain:latest

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
    proxychains4 \
    python3 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY railway-start.py /app/railway-start.py

EXPOSE 5000

ENTRYPOINT []
CMD ["python3", "/app/railway-start.py"]
