FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y bash curl && \
    curl -fsSL https://get.docker.com | sh && \
    rm -rf /var/lib/apt/lists/*

COPY server.py /app/server.py
WORKDIR /app

EXPOSE 5000

CMD ["python", "server.py"]