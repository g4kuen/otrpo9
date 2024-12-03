FROM python:3.9-slim


RUN apt-get update && apt-get install -y redis-server


WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 6379 8888

CMD service redis-server start && python backend.py
