FROM python:3.11-slim
WORKDIR /app
COPY network.py dedicated_server.py ./
CMD ["python", "dedicated_server.py"]
