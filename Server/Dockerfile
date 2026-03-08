FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY . .

RUN mkdir -p /var/log/terminal-server

CMD ["python3", "-u", "server.py"]
